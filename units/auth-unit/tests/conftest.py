"""SQLite-backed test fixtures. Uses aiosqlite so we exercise the real ORM."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from auth.models import Base, User, UserRole


@pytest.fixture
def admin_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def another_admin_id() -> UUID:
    return uuid4()


@pytest_asyncio.fixture
async def session(admin_user_id: UUID, another_admin_id: UUID) -> AsyncIterator[AsyncSession]:
    """SQLite in-memory DB; the PG UUID columns degrade to TEXT under sqlite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        # SQLite doesn't have a native UUID type; SQLAlchemy emits CHAR(32) here.
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        # Seed with two active admins so revoke-admin invariant tests have room.
        for uid in (admin_user_id, another_admin_id):
            s.add(
                User(
                    user_id=uid,
                    email=f"{uid}@example.test",
                    display_name="seed",
                    is_active=True,
                )
            )
            s.add(UserRole(user_id=uid, role="Admin"))
        await s.commit()
        yield s
    await engine.dispose()
