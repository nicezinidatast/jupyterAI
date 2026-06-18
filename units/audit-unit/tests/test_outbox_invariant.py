"""PBT — 발행된 모든 이벤트가 정확히 한 번 audit_log에 도달하는지 검증한다 (손실 없음).

검증 불변식:
  1. 이미터가 N개 이벤트를 outbox에 삽입한 뒤 컨슈머가 드레인하면 audit_log 행 수 == N.
  2. 드레인 완료 후 미전달(delivered_at IS NULL) outbox 행이 0개여야 한다.
  3. 빈 outbox에 드레인을 반복해도 0을 반환하며 부작용이 없어야 한다 (멱등성).
"""

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
    """인메모리 SQLite DB와 스키마를 생성하고 session_factory를 제공한다."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def test_outbox_to_log_no_loss(session_factory) -> None:
    """N개 이벤트 발행 → 단일 드레인 → audit_log 행 수 == N 불변식을 검증한다.

    홀수 인덱스 이벤트는 result='failure'로, 짝수는 'success'로 혼합해
    result 체크 제약도 통과하는지 함께 확인한다.
    """
    emitter = OutboxAuditEmitter()

    # N개 이벤트를 하나의 트랜잭션에 삽입한다.
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

    # 단일 드레인 패스 실행.
    consumer = OutboxConsumer(session_factory, batch=50, idle_sleep_s=0.01)
    processed = await consumer._drain_once()  # noqa: SLF001 — 단일 패스 직접 테스트
    assert processed == n

    # 불변식 검증: audit_log 행 수 == 발행 이벤트 수, 미전달 outbox == 0.
    async with session_factory() as session:
        log_count = await session.scalar(select(func.count()).select_from(AuditLog))
        undelivered = await session.scalar(
            select(func.count()).select_from(AuditOutbox).where(AuditOutbox.delivered_at.is_(None))
        )
    assert log_count == n
    assert undelivered == 0


async def test_drain_is_idempotent_when_empty(session_factory) -> None:
    """빈 outbox에 드레인을 반복해도 0을 반환하며 부작용이 없어야 한다."""
    consumer = OutboxConsumer(session_factory, batch=50, idle_sleep_s=0.01)
    assert await consumer._drain_once() == 0  # noqa: SLF001
    assert await consumer._drain_once() == 0  # noqa: SLF001
