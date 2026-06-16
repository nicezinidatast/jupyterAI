"""PBT — share link permission < required → always FORBIDDEN."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok
from dataplatform_shared.types.common import (
    CorrelationId,
    SessionId,
    UserContext,
    UserId,
)

from notebook.models import Base
from notebook.services.share_link import ShareLinkManager

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


def _ctx(user_id: str, roles: tuple[str, ...] = ("Viewer",)) -> UserContext:
    return UserContext(
        user_id=UserId(user_id),
        roles=roles,  # type: ignore[arg-type]
        session_id=SessionId("s"),
        corr_id=CorrelationId("c"),
    )


async def test_read_link_denies_execute(session: AsyncSession) -> None:
    mgr = ShareLinkManager(session)
    notebook_id = uuid4()
    owner = uuid4()
    consumer_id = uuid4()
    create = await mgr.create(
        notebook_id=notebook_id,
        permission="read",
        created_by=owner,
        audience_users=(consumer_id,),
    )
    assert isinstance(create, Ok)
    await session.commit()
    result = await mgr.resolve(create.value, _ctx(str(consumer_id)), required="execute")
    assert isinstance(result, Err)
    assert result.error == DomainError.FORBIDDEN


async def test_edit_link_allows_read(session: AsyncSession) -> None:
    mgr = ShareLinkManager(session)
    notebook_id = uuid4()
    owner = uuid4()
    consumer_id = uuid4()
    create = await mgr.create(
        notebook_id=notebook_id,
        permission="edit",
        created_by=owner,
        audience_users=(consumer_id,),
    )
    assert isinstance(create, Ok)
    await session.commit()
    result = await mgr.resolve(create.value, _ctx(str(consumer_id)), required="read")
    assert isinstance(result, Ok)


async def test_unknown_audience_forbidden(session: AsyncSession) -> None:
    mgr = ShareLinkManager(session)
    notebook_id = uuid4()
    owner = uuid4()
    intended = uuid4()
    other = uuid4()
    create = await mgr.create(
        notebook_id=notebook_id,
        permission="read",
        created_by=owner,
        audience_users=(intended,),
    )
    assert isinstance(create, Ok)
    await session.commit()
    result = await mgr.resolve(create.value, _ctx(str(other)), required="read")
    assert isinstance(result, Err)
    assert result.error == DomainError.FORBIDDEN


async def test_revoke_makes_link_not_found(session: AsyncSession) -> None:
    mgr = ShareLinkManager(session)
    notebook_id = uuid4()
    owner = uuid4()
    consumer = uuid4()
    create = await mgr.create(
        notebook_id=notebook_id,
        permission="read",
        created_by=owner,
        audience_users=(consumer,),
    )
    assert isinstance(create, Ok)
    await session.commit()
    revoke = await mgr.revoke(create.value)
    assert isinstance(revoke, Ok)
    await session.commit()
    result = await mgr.resolve(create.value, _ctx(str(consumer)), required="read")
    assert isinstance(result, Err)
