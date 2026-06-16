"""Role assignment with the 'at least one active Admin' invariant (US-AUTH-02)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result

from auth.models import User, UserRole, VALID_ROLES


class RoleResolver:
    """Manages user ↔ role mappings.

    Invariant: there is always ≥ 1 active user with role 'Admin'.
    Violations raise ``Err(CONFLICT)`` rather than silently leaving the system
    locked out.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_roles(self, user_id: UUID) -> Result[tuple[str, ...], DomainError]:
        rows = await self._session.scalars(
            select(UserRole.role).where(UserRole.user_id == user_id)
        )
        return Ok(tuple(rows.all()))

    async def assign_role(
        self, target_user_id: UUID, role: str
    ) -> Result[None, DomainError]:
        if role not in VALID_ROLES:
            return Err(DomainError.VALIDATION)
        # Idempotent — duplicate insert is a no-op.
        existing = await self._session.scalar(
            select(UserRole).where(
                and_(UserRole.user_id == target_user_id, UserRole.role == role)
            )
        )
        if existing is None:
            self._session.add(UserRole(user_id=target_user_id, role=role))
            await self._session.flush()
        return Ok(None)

    async def revoke_role(
        self, target_user_id: UUID, role: str
    ) -> Result[None, DomainError]:
        if role not in VALID_ROLES:
            return Err(DomainError.VALIDATION)

        if role == "Admin":
            # Lock the *other* active admin rows so two concurrent requests
            # cannot both observe other_admins == 1 and proceed to leave the
            # system with zero admins. ``FOR UPDATE`` serialises the count on
            # Postgres; on sqlite (the test fixture) the clause is silently
            # ignored, which is fine because sqlite is single-writer anyway.
            lock_stmt = (
                select(UserRole.user_id)
                .join(User, User.user_id == UserRole.user_id)
                .where(
                    and_(
                        UserRole.role == "Admin",
                        UserRole.user_id != target_user_id,
                        User.is_active.is_(True),
                    )
                )
            )
            try:
                lock_stmt = lock_stmt.with_for_update()
            except Exception:  # pragma: no cover — dialect without FOR UPDATE
                pass
            other_admin_ids = (await self._session.execute(lock_stmt)).scalars().all()
            if len(other_admin_ids) < 1:
                return Err(DomainError.CONFLICT)

        await self._session.execute(
            delete(UserRole).where(
                and_(UserRole.user_id == target_user_id, UserRole.role == role)
            )
        )
        return Ok(None)
