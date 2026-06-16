"""Thin orchestration around RoleResolver — used by other units to check access."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.kernel_iface import Action, Resource
from dataplatform_shared.types.common import UserContext

from auth.services.role_resolver import RoleResolver

# Coarse role policy. Resource-level policies (connection grants, share-link
# audiences) are evaluated by the owning units (data-unit / notebook-unit).
_ROLE_POLICY: dict[tuple[Action, str], frozenset[str]] = {
    ("admin", "system"): frozenset({"Admin"}),
    ("read", "audit"): frozenset({"Admin", "Auditor"}),
    ("write", "audit"): frozenset(),  # nobody writes to audit logs directly
    ("read", "connection"): frozenset({"Admin", "Analyst", "Auditor"}),
    ("execute", "connection"): frozenset({"Admin", "Analyst"}),
    ("read", "notebook"): frozenset({"Admin", "Analyst", "Viewer"}),
    ("write", "notebook"): frozenset({"Admin", "Analyst"}),
}


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._roles = RoleResolver(session)

    async def verify_access(
        self, ctx: UserContext, action: Action, resource: Resource
    ) -> Result[None, DomainError]:
        allowed = _ROLE_POLICY.get((action, resource.kind))
        if allowed is None:
            # Default deny on unknown combinations (fail-closed, SECURITY-15).
            return Err(DomainError.FORBIDDEN)
        if not any(r in allowed for r in ctx.roles):
            return Err(DomainError.FORBIDDEN)
        return Ok(None)

    async def change_role(
        self, target: UUID, role: str, op: str
    ) -> Result[None, DomainError]:
        if op == "assign":
            return await self._roles.assign_role(target, role)
        if op == "revoke":
            return await self._roles.revoke_role(target, role)
        return Err(DomainError.VALIDATION)
