"""PRD US-CODE-09 — Credential 상태 기계(state machine) 검증 (PBT 스타일).

상태 전이 경로: register → rotate → delete.
검증 불변식:
  - delete 이후 resolve는 NOT_FOUND를 반환해야 한다.
  - rotate 이후 캐시는 무효화되어 새 시크릿이 반환되어야 한다.
  - 타 사용자가 personal Credential에 접근하면 FORBIDDEN이어야 한다.
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
    """테스트용 UserContext 헬퍼 — 실제 인증 없이 user_id만 지정한다."""
    return UserContext(
        user_id=UserId(user_id),
        roles=("Analyst",),
        session_id=SessionId("s-1"),
        corr_id=CorrelationId("c-1"),
    )


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """인메모리 SQLite DB를 생성하고 스키마를 적용한 세션을 제공한다."""
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
    """register → rotate → delete 전체 생애주기 후 resolve가 NOT_FOUND를 반환하는지 검증한다.

    각 단계에서 시크릿 값이 올바르게 반영되는지도 함께 확인한다:
      - register 직후 resolve: 초기 값(pw1) 반환
      - rotate 직후 resolve: 신규 값(pw2) 반환 (캐시 무효화 확인)
      - delete 직후 resolve: NOT_FOUND 반환
    """
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
    """소유자가 아닌 다른 사용자가 personal Credential에 접근하면 FORBIDDEN이어야 한다.

    shared Credential의 접근 제어는 data-unit의 connection grant로 별도 처리되며
    이 테스트는 personal 스코프의 owner 격리만 검증한다.
    """
    vault = InMemoryVaultAdapter()
    svc = CredentialVault(session=session, vault=vault, cache=ResolveCache(ttl_seconds=1))
    owner = uuid4()
    other = _ctx(str(uuid4()))

    reg = await svc.register(scope="personal", name="db1", secret=Secret("pw1"), owner_user_id=owner)
    assert isinstance(reg, Ok)
    await session.commit()

    r = await svc.resolve(reg.value, other)
    assert isinstance(r, Err) and r.error == DomainError.FORBIDDEN
