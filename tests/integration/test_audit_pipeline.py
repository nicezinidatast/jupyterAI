"""outbox → audit_log 파이프라인의 실제 postgres 통합 테스트.

audit-unit 의 ``OutboxAuditEmitter`` 로 도메인 변경과 동일 트랜잭션에서 이벤트를 기록하고,
컨슈머의 drain 루프를 한 번 실행한 뒤, 결과 ``audit_log`` 행이 올바른지 검증한다.

outbox 패턴의 계약:
  - emit 은 outbox 테이블에 쓰고 즉시 delivered 는 아니다.
  - _drain_once 가 배치로 outbox 를 읽어 audit_log 로 이관하고 delivered_at 을 설정한다.
  - drain 은 멱등적이어야 한다(빈 outbox 에서는 0 을 반환한다).
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def test_outbox_emit_then_consumer_drains(fresh_session_factory) -> None:
    """emit → _drain_once → audit_log 행 생성의 전체 outbox 파이프라인을 검증한다.

    불변식:
    - emit 직후 outbox 행이 1개 존재하고 delivered_at 이 None 이다.
    - _drain_once 가 1 을 반환한다(drain 된 항목 수).
    - drain 후 audit_log 에 올바른 필드 값의 행이 1개 생성된다.
    - drain 후 outbox 행의 delivered_at 이 채워진다.
    """
    from audit.consumer import OutboxConsumer
    from audit.emitter import OutboxAuditEmitter
    from audit.models import AuditLog, AuditOutbox
    from dataplatform_shared.audit.events import make_event

    emitter = OutboxAuditEmitter()
    event = make_event(
        type="connection_created",
        actor="itest-user",
        result="success",
        corr_id="itest-corr-1",
        resource="conn://itest",
        payload={"row_data_transmitted": False},
    )

    async with fresh_session_factory() as session:
        await emitter.emit(session, event)
        await session.commit()

    async with fresh_session_factory() as session:
        outbox_rows = (await session.execute(select(AuditOutbox))).scalars().all()
    assert len(outbox_rows) == 1
    assert outbox_rows[0].delivered_at is None

    consumer = OutboxConsumer(fresh_session_factory, batch=10)
    drained = await consumer._drain_once()
    assert drained == 1

    async with fresh_session_factory() as session:
        log_rows = (await session.execute(select(AuditLog))).scalars().all()
        outbox_after = (await session.execute(select(AuditOutbox))).scalars().all()

    assert len(log_rows) == 1
    row = log_rows[0]
    assert row.event_type == "connection_created"
    assert row.actor_id == "itest-user"
    assert row.resource == "conn://itest"
    assert row.result == "success"
    assert row.corr_id == "itest-corr-1"
    assert row.payload == {"row_data_transmitted": False}
    assert outbox_after[0].delivered_at is not None


async def test_consumer_is_idempotent_when_outbox_empty(fresh_session_factory) -> None:
    """빈 outbox 에서 drain 은 0 을 반환하고 오류 없이 종료한다.

    outbox 가 비어 있을 때 컨슈머가 예외를 던지면 백그라운드 루프 전체가 중단된다.
    이 테스트는 그 안전 계약을 보장한다.
    """
    from audit.consumer import OutboxConsumer

    consumer = OutboxConsumer(fresh_session_factory, batch=10)
    drained = await consumer._drain_once()
    assert drained == 0


async def test_consumer_drains_batch_in_order(fresh_session_factory) -> None:
    """2개 이벤트가 삽입 순서대로 drain 되고, 두 번째 drain 은 0 을 반환함을 검증한다.

    순서 보장: audit_log 의 id 기준 정렬이 outbox 삽입 순서와 일치해야 한다.
    멱등성: 동일 배치를 두 번 drain 해도 중복 레코드가 생기지 않는다.
    """
    from audit.consumer import OutboxConsumer
    from audit.emitter import OutboxAuditEmitter
    from audit.models import AuditLog
    from dataplatform_shared.audit.events import make_event
    from sqlalchemy import select

    emitter = OutboxAuditEmitter()
    for i in range(2):
        evt = make_event(
            type=f"evt_{i}",
            actor="itest",
            result="success",
            corr_id=f"corr-{i}",
            payload={"i": i},
        )
        async with fresh_session_factory() as session:
            await emitter.emit(session, evt)
            await session.commit()

    consumer = OutboxConsumer(fresh_session_factory, batch=10)
    assert await consumer._drain_once() == 2
    # Second drain is a no-op.
    assert await consumer._drain_once() == 0

    async with fresh_session_factory() as session:
        logs = (await session.execute(select(AuditLog).order_by(AuditLog.id))).scalars().all()
    assert [log.event_type for log in logs] == ["evt_0", "evt_1"]
