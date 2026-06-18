"""PRD US-CODE-09 — 등록 충돌 계약(PBT: Property-Based Testing 스타일) 검증.

register가 충돌 시 멱등하게 CONFLICT를 반환하는지 확인한다.
전체 생애주기(register → rotate → delete) 테스트는 ``test_lifecycle.py`` 에 있으며,
이 파일은 충돌 수용 기준을 독립적으로 드러내기 위해 분리되었다.
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
    """인메모리 SQLite DB를 생성하고 스키마를 적용한 세션을 제공한다.

    테스트 종료 후 engine.dispose()로 커넥션을 정리한다.
    """
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
    """같은 소유자가 동일 이름으로 두 번 등록하면 두 번째가 CONFLICT를 반환해야 한다.

    첫 번째 등록 후 session.commit()으로 DB에 확정한 뒤 두 번째 등록을 시도한다.
    uq_cred_name 제약이 IntegrityError를 발생시켜 CONFLICT로 변환되는 경로를 검증한다.
    """
    vault = InMemoryVaultAdapter()
    svc = CredentialVault(session=session, vault=vault, cache=ResolveCache(ttl_seconds=1))
    owner = uuid4()
    r1 = await svc.register(scope="personal", name="db1", secret=Secret("pw1"), owner_user_id=owner)
    await session.commit()
    r2 = await svc.register(scope="personal", name="db1", secret=Secret("pw2"), owner_user_id=owner)
    assert isinstance(r1, Ok)
    assert isinstance(r2, Err) and r2.error == DomainError.CONFLICT


async def test_invalid_scope_returns_validation(session: AsyncSession) -> None:
    """허용되지 않는 scope 값은 서비스 레이어에서 VALIDATION 오류로 즉시 거부되어야 한다."""
    vault = InMemoryVaultAdapter()
    svc = CredentialVault(session=session, vault=vault, cache=ResolveCache(ttl_seconds=1))
    r = await svc.register(scope="bogus", name="x", secret=Secret("pw"), owner_user_id=None)
    assert isinstance(r, Err) and r.error == DomainError.VALIDATION
