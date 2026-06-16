"""PBT — every emitted event lands in audit_log exactly once (no loss)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dataplatform_shared.audit.events import make_event

from audit.consumer import OutboxConsumer
from audit.emitter import OutboxAuditEmitter
from audit.models import AuditLog, AuditOutbox, Base

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def test_outbox_to_log_no_loss(session_factory) -> None:
    emitter = OutboxAuditEmitter()

    # Emit N events in N small transactions.
    n = 17
    async with session_factory() as session:
        async with session.begin():
            for i in range(n):
                await emitter.emit(
                    session,
                    make_event(
                        type=f"e_{i}",
                        actor=f"u_{i}",
                        result="success" if i % 2 == 0 else "failure",
                        corr_id=f"c_{i}",
                        payload={"i": i},
                    ),
                )

    # Drain once.
    consumer = OutboxConsumer(session_factory, batch=50, idle_sleep_s=0.01)
    processed = await consumer._drain_once()  # noqa: SLF001 — exercising single pass
    assert processed == n

    # Invariant: audit_log row count == events emitted.
    async with session_factory() as session:
        log_count = await session.scalar(select(func.count()).select_from(AuditLog))
        undelivered = await session.scalar(
            select(func.count()).select_from(AuditOutbox).where(AuditOutbox.delivered_at.is_(None))
        )
    assert log_count == n
    assert undelivered == 0


async def test_drain_is_idempotent_when_empty(session_factory) -> None:
    consumer = OutboxConsumer(session_factory, batch=50, idle_sleep_s=0.01)
    assert await consumer._drain_once() == 0  # noqa: SLF001
    assert await consumer._drain_once() == 0  # noqa: SLF001
