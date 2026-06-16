"""Real-postgres integration for the outbox → audit_log pipeline.

We use the actual audit-unit ``OutboxAuditEmitter`` to write an event in the
same transaction as a domain change, run the consumer's drain loop once, and
assert the resulting ``audit_log`` row matches.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def test_outbox_emit_then_consumer_drains(fresh_session_factory) -> None:
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
    """Empty drain returns 0 and never errors."""
    from audit.consumer import OutboxConsumer

    consumer = OutboxConsumer(fresh_session_factory, batch=10)
    drained = await consumer._drain_once()
    assert drained == 0


async def test_consumer_drains_batch_in_order(fresh_session_factory) -> None:
    """Two events written → drained in insertion order, only once."""
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
