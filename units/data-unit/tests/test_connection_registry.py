"""PBT — RBAC invariant: a connection without a matching grant is invisible.

The connection_grants table is the authoritative ACL. A user (or any role
they hold) must have at least one grant whose ``action`` covers the requested
operation; otherwise the connection is filtered out of list() and access is
denied to get().

This unit test exercises the ACL filtering in isolation, with sqlite as the
backing store; the real registry service uses the same SQL.
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
    """The RBAC-aware listing query the real service uses (kept inline so the
    test pins the SQL shape directly)."""
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
    """Invariant: a user with no grant sees zero connections — no matter how
    many connections exist in the table."""
    user_id = uuid4()
    # Seed three connections, none of which the user has a grant for.
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
    """PBT: for any number of connections, a user with no grants sees nothing."""
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
