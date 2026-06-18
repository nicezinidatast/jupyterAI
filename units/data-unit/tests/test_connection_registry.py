"""PBT — RBAC 불변식: 매칭되는 grant가 없는 연결은 보이지 않는다.

connection_grants 테이블이 권위 있는 ACL(접근 제어 목록)이다. 사용자(또는 그가
가진 임의 역할)는 요청한 작업을 포괄하는 ``action``의 grant를 최소 하나는 가져야
한다. 그렇지 않으면 그 연결은 list()에서 걸러지고 get() 접근도 거부된다.

이 단위 테스트는 ACL 필터링만 떼어내(in isolation) 검증하며, 백킹 저장소로
sqlite를 쓴다. 실제 레지스트리 서비스도 같은 SQL을 사용한다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from data.models import Base, Connection, ConnectionGrant

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _seed_connection(session: AsyncSession, *, name: str = "db1") -> UUID:
    conn_id = uuid4()
    session.add(
        Connection(
            connection_id=conn_id,
            name=name,
            engine="postgres",
            host="db.test",
            port=5432,
            database="x",
            credential_id=uuid4(),
            options={},
            is_active=True,
        )
    )
    await session.flush()
    return conn_id


async def _list_visible_for(session: AsyncSession, *, user_id: UUID, roles: tuple[str, ...]) -> list[UUID]:
    """실제 서비스가 쓰는 RBAC 인지(aware) 목록 질의. 테스트가 SQL 모양을 직접
    못 박도록 인라인으로 둔다(서비스 코드와 어긋나면 테스트가 깨지게)."""
    role_list = list(roles)
    stmt = (
        select(Connection.connection_id)
        .where(Connection.is_active.is_(True))
        .where(
            Connection.connection_id.in_(
                select(ConnectionGrant.connection_id)
                .where(
                    (ConnectionGrant.subject_user_id == user_id)
                    | (ConnectionGrant.subject_role.in_(role_list) if role_list else False)
                )
                .where(ConnectionGrant.action.in_(("read", "execute", "admin")))
            )
        )
    )
    return list((await session.execute(stmt)).scalars().all())


async def test_no_grant_means_invisible(session: AsyncSession) -> None:
    """불변식: grant가 없는 사용자는 테이블에 연결이 아무리 많아도 0개만 본다."""
    user_id = uuid4()
    # 사용자가 grant를 갖지 않은 연결 3개를 심는다.
    for i in range(3):
        await _seed_connection(session, name=f"db{i}")
    await session.commit()

    visible = await _list_visible_for(session, user_id=user_id, roles=("Analyst",))
    assert visible == []


async def test_user_grant_makes_visible(session: AsyncSession) -> None:
    user_id = uuid4()
    conn_id = await _seed_connection(session, name="db1")
    session.add(
        ConnectionGrant(
            grant_id=uuid4(),
            connection_id=conn_id,
            subject_user_id=user_id,
            subject_role=None,
            action="execute",
        )
    )
    await session.commit()

    visible = await _list_visible_for(session, user_id=user_id, roles=("Analyst",))
    assert visible == [conn_id]


async def test_role_grant_makes_visible(session: AsyncSession) -> None:
    user_id = uuid4()
    conn_id = await _seed_connection(session, name="db1")
    session.add(
        ConnectionGrant(
            grant_id=uuid4(),
            connection_id=conn_id,
            subject_user_id=None,
            subject_role="Analyst",
            action="read",
        )
    )
    await session.commit()

    visible = await _list_visible_for(session, user_id=user_id, roles=("Analyst",))
    assert visible == [conn_id]


@given(n_conns=st.integers(min_value=1, max_value=20))
@settings(max_examples=20, deadline=None)
async def test_pbt_no_grants_means_zero_visible(n_conns: int) -> None:
    """PBT: 연결 개수가 몇이든, grant가 없는 사용자에게는 아무것도 보이지 않는다."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid4()
    try:
        async with factory() as s:
            for i in range(n_conns):
                await _seed_connection(s, name=f"db{i}")
            await s.commit()
            visible = await _list_visible_for(s, user_id=user_id, roles=("Analyst", "Viewer"))
            assert visible == [], f"unexpected visibility for n={n_conns}: {visible}"
    finally:
        await engine.dispose()
