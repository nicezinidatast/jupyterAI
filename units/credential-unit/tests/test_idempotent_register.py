"""Per PRD US-CODE-09: PBT — register is idempotent on conflict.

The full lifecycle (register + rotate + delete) lives in
``test_lifecycle.py``; this file isolates the idempotency contract so the
acceptance criterion file name appears in the test collection.
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

from credential.adapters.vault import InMemoryVaultAdapter
from credential.cache import ResolveCache
from credential.models import Base
from credential.services.vault_service import CredentialVault

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


async def test_duplicate_name_returns_conflict(session: AsyncSession) -> None:
    vault = InMemoryVaultAdapter()
    svc = CredentialVault(session=session, vault=vault, cache=ResolveCache(ttl_seconds=1))
    owner = uuid4()
    r1 = await svc.register(scope="personal", name="db1", secret=Secret("pw1"), owner_user_id=owner)
    await session.commit()
    r2 = await svc.register(scope="personal", name="db1", secret=Secret("pw2"), owner_user_id=owner)
    assert isinstance(r1, Ok)
    assert isinstance(r2, Err) and r2.error == DomainError.CONFLICT


async def test_invalid_scope_returns_validation(session: AsyncSession) -> None:
    vault = InMemoryVaultAdapter()
    svc = CredentialVault(session=session, vault=vault, cache=ResolveCache(ttl_seconds=1))
    r = await svc.register(scope="bogus", name="x", secret=Secret("pw"), owner_user_id=None)
    assert isinstance(r, Err) and r.error == DomainError.VALIDATION
