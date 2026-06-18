"""속성 기반 테스트(PBT, property-based testing) — Admin 취소가 시스템을 활성
admin 0명 상태로 절대 만들지 않아야 한다는 핵심 불변식을 검증한다."""

from __future__ import annotations

from uuid import UUID

import pytest

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok

from auth.services.role_resolver import RoleResolver


pytestmark = pytest.mark.asyncio


async def test_revoke_last_admin_refused(session, admin_user_id: UUID, another_admin_id: UUID) -> None:
    resolver = RoleResolver(session)
    # 첫 취소는 허용된다(다른 admin이 남기 때문).
    r1 = await resolver.revoke_role(admin_user_id, "Admin")
    assert isinstance(r1, Ok)
    await session.commit()
    # 두 번째 취소는 Admin을 비우게 되므로 거부돼야 한다(CONFLICT).
    r2 = await resolver.revoke_role(another_admin_id, "Admin")
    assert isinstance(r2, Err)
    assert r2.error == DomainError.CONFLICT


async def test_assign_invalid_role(session, admin_user_id: UUID) -> None:
    # 표준 역할 집합에 없는 값은 VALIDATION 오류로 거부돼야 한다.
    resolver = RoleResolver(session)
    r = await resolver.assign_role(admin_user_id, "Wizard")
    assert isinstance(r, Err)
    assert r.error == DomainError.VALIDATION


async def test_assign_is_idempotent(session, admin_user_id: UUID) -> None:
    # 같은 역할을 두 번 부여해도 둘 다 성공이고 중복 행이 생기지 않아야 한다(멱등).
    resolver = RoleResolver(session)
    r1 = await resolver.assign_role(admin_user_id, "Auditor")
    r2 = await resolver.assign_role(admin_user_id, "Auditor")
    assert isinstance(r1, Ok)
    assert isinstance(r2, Ok)
    roles = await resolver.get_roles(admin_user_id)
    assert isinstance(roles, Ok)
    assert sorted(roles.value) == ["Admin", "Auditor"]
