"""audit_log 검색 + 내보내기 서비스 — AuditorConsole 백엔드가 사용한다.

이 모듈은 읽기 전용(read-only) 서비스다. audit_log는 WORM(Write Once Read Many)
트리거로 보호되므로 여기서도 UPDATE/DELETE는 시도하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Ok, Result

from audit.models import AuditLog


@dataclass(frozen=True, slots=True)
class AuditFilter:
    """audit_log 검색 필터 — 모든 필드는 선택적이다.

    frozen=True: 한 번 생성된 필터는 변경 불가하여 의도치 않은 재사용 변이를 막는다.
    slots=True: __dict__ 없이 슬롯 기반 메모리를 사용해 대량 생성 비용을 줄인다.
    """

    actor_id: str | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None
    # event_types/resources를 tuple로 받는 이유: IN 절에 바로 전달할 수 있고
    # 불변 컨테이너라 frozen dataclass와 일관성이 있기 때문이다.
    event_types: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()


class AuditQueryApi:
    """audit_log에 대한 페이지네이션 검색과 직렬화를 담당하는 쿼리 서비스."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self, filt: AuditFilter, *, page: int = 0, page_size: int = 100
    ) -> Result[list[dict], DomainError]:
        """주어진 필터 조건으로 audit_log를 검색해 최신순으로 반환한다.

        각 필터는 독립적으로 적용되며(AND 조건), 빈 컬렉션(event_types, resources)은
        해당 조건을 무시한다.
        """
        stmt = select(AuditLog)
        if filt.actor_id:
            stmt = stmt.where(AuditLog.actor_id == filt.actor_id)
        if filt.from_at:
            stmt = stmt.where(AuditLog.occurred_at >= filt.from_at)
        if filt.to_at:
            stmt = stmt.where(AuditLog.occurred_at <= filt.to_at)
        if filt.event_types:
            stmt = stmt.where(AuditLog.event_type.in_(filt.event_types))
        if filt.resources:
            stmt = stmt.where(AuditLog.resource.in_(filt.resources))
        stmt = stmt.order_by(AuditLog.occurred_at.desc()).limit(page_size).offset(page * page_size)
        rows = (await self._session.execute(stmt)).scalars().all()
        return Ok([self._serialize(r) for r in rows])

    @staticmethod
    def _serialize(row: AuditLog) -> dict:
        """AuditLog ORM 객체를 API 응답용 dict로 변환한다."""
        return {
            "id": row.id,
            "event_type": row.event_type,
            "actor_id": row.actor_id,
            "resource": row.resource,
            "result": row.result,
            "occurred_at": row.occurred_at.isoformat(),
            "corr_id": row.corr_id,
            "payload": row.payload,
        }
