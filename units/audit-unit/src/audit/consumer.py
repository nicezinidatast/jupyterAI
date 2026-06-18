"""백그라운드 컨슈머 — outbox 테이블에서 audit_log로 이벤트를 이관한다.

``SELECT ... FOR UPDATE SKIP LOCKED`` 를 사용해 여러 워커가 병렬로 실행될 때
같은 행을 중복 처리하지 않도록 한다. 이미 잠긴 행은 건너뛰므로 한 워커가
느려도 다른 워커가 블로킹되지 않는다.

SQLite 폴백: SKIP LOCKED는 Postgres 전용 구문이다. SQLite 테스트 환경에서는
with_for_update()가 예외를 던지며 이를 조용히 무시해 일반 SELECT로 동작한다.
단일 컨슈머만 사용하는 테스트에서는 락이 불필요하므로 기능적으로 동일하다.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.telemetry import get_logger

from audit.models import AuditLog, AuditOutbox

logger = get_logger("audit.consumer")


class OutboxConsumer:
    """Outbox 행을 배치로 읽어 audit_log에 삽입하는 백그라운드 루프.

    batch: 한 번의 _drain_once 호출에서 처리할 최대 행 수.
    idle_sleep_s: 처리할 행이 없을 때 대기할 초 단위 시간.
    _stopped: asyncio.Event로 graceful shutdown을 구현한다.
    """

    def __init__(self, session_factory, *, batch: int = 100, idle_sleep_s: float = 5.0) -> None:
        self._session_factory = session_factory
        self._batch = batch
        self._idle_sleep_s = idle_sleep_s
        self._stopped = asyncio.Event()

    def stop(self) -> None:
        """외부에서 컨슈머를 정지시킨다. run() 루프가 현재 배치 완료 후 종료된다."""
        self._stopped.set()

    async def run(self) -> None:
        """컨슈머 메인 루프 — stop()이 호출되거나 외부에서 태스크가 취소될 때까지 실행된다.

        처리할 행이 없으면 idle_sleep_s 동안 대기하되, 그 사이 stop()이 호출되면
        즉시 종료한다 (wait_for + stopped.wait 조합).
        """
        while not self._stopped.is_set():
            processed = await self._drain_once()
            if processed == 0:
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=self._idle_sleep_s)
                except TimeoutError:
                    pass

    async def _drain_once(self) -> int:
        """미전달(delivered_at IS NULL) outbox 행을 배치 처리하고 처리 수를 반환한다.

        한 트랜잭션 안에서 읽기 → audit_log 삽입 → delivered_at 갱신을 원자적으로 수행한다.
        트랜잭션 실패 시 모든 변경이 롤백되므로 행이 미전달 상태로 남아 재처리된다
        — at-least-once 보장의 핵심이다.
        """
        async with self._session_factory() as session:  # type: AsyncSession
            async with session.begin():
                stmt = (
                    select(AuditOutbox)
                    .where(AuditOutbox.delivered_at.is_(None))
                    .order_by(AuditOutbox.id)
                    .limit(self._batch)
                )
                # FOR UPDATE SKIP LOCKED는 Postgres 전용이다. SQLite에서는 무시한다.
                try:
                    stmt = stmt.with_for_update(skip_locked=True)
                except Exception:  # noqa: BLE001
                    pass
                rows = (await session.execute(stmt)).scalars().all()
                if not rows:
                    return 0
                for row in rows:
                    event = row.event
                    await session.execute(
                        insert(AuditLog).values(
                            event_type=event["type"],
                            actor_id=event["actor"],
                            resource=event.get("resource"),
                            result=event["result"],
                            occurred_at=_parse_at(event["at"]),
                            corr_id=event.get("corr_id"),
                            payload=event.get("payload", {}),
                        )
                    )
                    # delivered_at을 채워 이 행이 다음 드레인에서 다시 선택되지 않도록 한다.
                    await session.execute(
                        update(AuditOutbox)
                        .where(AuditOutbox.id == row.id)
                        .values(delivered_at=func.now())
                    )
                logger.info("audit_drained", count=len(rows))
                return len(rows)


def _parse_at(value: str) -> datetime:
    """ISO 8601 문자열을 timezone-aware datetime으로 변환한다.

    Z 접미사(UTC 표기)와 +HH:MM 오프셋 형식을 모두 수용한다.
    Python 3.10 이하에서 fromisoformat()이 Z를 지원하지 않아 수동으로 치환한다.
    """
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.fromisoformat(value).astimezone(UTC)
