"""SQLite 기반 테스트 픽스처. aiosqlite를 써서 실제 ORM 경로를 그대로 검증한다.

목(mock)이 아니라 진짜 비동기 SQLite로 ORM·쿼리를 실행하므로, Postgres와의
방언 차이만 빼면 운영과 같은 코드 경로를 탄다.
"""

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
    """인메모리 SQLite DB. PG의 UUID 컬럼은 sqlite에서 TEXT로 강등된다.

    테스트마다 새 인메모리 엔진을 만들어 격리를 보장하고, 끝나면 폐기한다.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        # SQLite에는 네이티브 UUID 타입이 없어 SQLAlchemy가 CHAR(32)로 발행한다.
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        # 활성 admin 2명으로 시드한다 — revoke-admin 불변식 테스트가 "한 명을
        # 지워도 다른 한 명이 남는" 경계를 검증할 여지를 두기 위함이다.
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
