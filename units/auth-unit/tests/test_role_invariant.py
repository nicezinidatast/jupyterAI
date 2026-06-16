"""PBT — revoking Admin must never leave the system with 0 active admins."""

from __future__ import annotations

from uuid import UUID

import pytest

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok

from auth.services.role_resolver import RoleResolver


pytestmark = pytest.mark.asyncio


async def test_revoke_last_admin_refused(session, admin_user_id: UUID, another_admin_id: UUID) -> None:
    resolver = RoleResolver(session)
    # First revocation is allowed (other admin remains).
    r1 = await resolver.revoke_role(admin_user_id, "Admin")
    assert isinstance(r1, Ok)
    await session.commit()
    # Second revocation would empty Admin — must be refused.
    r2 = await resolver.revoke_role(another_admin_id, "Admin")
    assert isinstance(r2, Err)
    assert r2.error == DomainError.CONFLICT


async def test_assign_invalid_role(session, admin_user_id: UUID) -> None:
    resolver = RoleResolver(session)
    r = await resolver.assign_role(admin_user_id, "Wizard")
    assert isinstance(r, Err)
    assert r.error == DomainError.VALIDATION


async def test_assign_is_idempotent(session, admin_user_id: UUID) -> None:
    resolver = RoleResolver(session)
    r1 = await resolver.assign_role(admin_user_id, "Auditor")
    r2 = await resolver.assign_role(admin_user_id, "Auditor")
    assert isinstance(r1, Ok)
    assert isinstance(r2, Ok)
    roles = await resolver.get_roles(admin_user_id)
    assert isinstance(roles, Ok)
    assert sorted(roles.value) == ["Admin", "Auditor"]
