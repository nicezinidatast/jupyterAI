"""Per PRD US-CODE-09: PBT — credential state machine.

State transitions: register → rotate → delete.  After delete, resolve must
return NOT_FOUND, and the cache must be invalidated.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok
from dataplatform_shared.security.secret import Secret
from dataplatform_shared.types.common import (
    CorrelationId,
    SessionId,
    UserContext,
    UserId,
)

from credential.adapters.vault import InMemoryVaultAdapter
from credential.cache import ResolveCache
from credential.models import Base
from credential.services.vault_service import CredentialVault

pytestmark = pytest.mark.asyncio


def _ctx(user_id: str) -> UserContext:
    return UserContext(
        user_id=UserId(user_id),
        roles=("Analyst",),
        session_id=SessionId("s-1"),
        corr_id=CorrelationId("c-1"),
    )


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


async def test_register_rotate_delete_then_resolve_not_found(session: AsyncSession) -> None:
    vault = InMemoryVaultAdapter()
    svc = CredentialVault(session=session, vault=vault, cache=ResolveCache(ttl_seconds=1))
    owner = uuid4()
    ctx = _ctx(str(owner))

    reg = await svc.register(scope="personal", name="db1", secret=Secret("pw1"), owner_user_id=owner)
    assert isinstance(reg, Ok)
    cred_id = reg.value
    await session.commit()

    resolve_initial = await svc.resolve(cred_id, ctx)
    assert isinstance(resolve_initial, Ok)
    assert resolve_initial.value.reveal() == "pw1"

    rotate = await svc.rotate(cred_id, Secret("pw2"))
    assert isinstance(rotate, Ok)
    await session.commit()
    resolve_rotated = await svc.resolve(cred_id, ctx)
    assert isinstance(resolve_rotated, Ok)
    assert resolve_rotated.value.reveal() == "pw2"

    delete = await svc.delete(cred_id)
    assert isinstance(delete, Ok)
    await session.commit()
    resolve_after_delete = await svc.resolve(cred_id, ctx)
    assert isinstance(resolve_after_delete, Err)
    assert resolve_after_delete.error == DomainError.NOT_FOUND


async def test_resolve_other_users_personal_is_forbidden(session: AsyncSession) -> None:
    vault = InMemoryVaultAdapter()
    svc = CredentialVault(session=session, vault=vault, cache=ResolveCache(ttl_seconds=1))
    owner = uuid4()
    other = _ctx(str(uuid4()))

    reg = await svc.register(scope="personal", name="db1", secret=Secret("pw1"), owner_user_id=owner)
    assert isinstance(reg, Ok)
    await session.commit()

    r = await svc.resolve(reg.value, other)
    assert isinstance(r, Err) and r.error == DomainError.FORBIDDEN
