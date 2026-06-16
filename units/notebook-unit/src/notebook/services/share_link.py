"""ShareLinkManager — enforces the permission >= required invariant.

A share link with permission ``read`` MUST NEVER grant ``execute`` or ``edit``,
even on a token replay.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.types.common import UserContext

from notebook.models import ShareAudience, ShareLink

Permission = Literal["read", "execute", "edit"]
_PERM_ORDER: dict[Permission, int] = {"read": 1, "execute": 2, "edit": 3}


@dataclass(frozen=True, slots=True)
class NotebookAccess:
    link_id: UUID
    notebook_id: UUID
    permission: Permission
    use_current_user_credentials: bool = True


class ShareLinkManager:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        notebook_id: UUID,
        permission: Permission,
        created_by: UUID,
        audience_users: tuple[UUID, ...] = (),
        audience_roles: tuple[str, ...] = (),
    ) -> Result[UUID, DomainError]:
        if permission not in _PERM_ORDER:
            return Err(DomainError.VALIDATION)
        if not audience_users and not audience_roles:
            return Err(DomainError.VALIDATION)
        link_id = uuid4()
        self._session.add(
            ShareLink(
                link_id=link_id,
                notebook_id=notebook_id,
                permission=permission,
                created_by=created_by,
            )
        )
        for u in audience_users:
            self._session.add(
                ShareAudience(link_id=link_id, subject_user_id=u, subject_role=None)
            )
        for r in audience_roles:
            self._session.add(
                ShareAudience(link_id=link_id, subject_user_id=None, subject_role=r)
            )
        await self._session.flush()
        return Ok(link_id)

    async def revoke(self, link_id: UUID) -> Result[None, DomainError]:
        from sqlalchemy import func as sql_func

        link = await self._session.get(ShareLink, link_id)
        if link is None:
            return Err(DomainError.NOT_FOUND)
        if link.revoked_at is None:
            link.revoked_at = sql_func.now()  # type: ignore[assignment]
        return Ok(None)

    async def resolve(
        self,
        link_id: UUID,
        requester: UserContext,
        required: Permission,
    ) -> Result[NotebookAccess, DomainError]:
        link = await self._session.get(ShareLink, link_id)
        if link is None or link.revoked_at is not None:
            return Err(DomainError.NOT_FOUND)
        # Invariant: granted permission must be ≥ required.
        if _PERM_ORDER[link.permission] < _PERM_ORDER[required]:
            return Err(DomainError.FORBIDDEN)

        # Audience match: either the requester's UUID or one of their roles.
        match_stmt = select(ShareAudience).where(ShareAudience.link_id == link_id)
        rows = (await self._session.execute(match_stmt)).scalars().all()
        if not rows:
            return Err(DomainError.FORBIDDEN)
        for row in rows:
            if row.subject_user_id and str(row.subject_user_id) == str(requester.user_id):
                return Ok(_to_access(link))
            if row.subject_role and row.subject_role in requester.roles:
                return Ok(_to_access(link))
        return Err(DomainError.FORBIDDEN)


def _to_access(link: ShareLink) -> NotebookAccess:
    return NotebookAccess(
        link_id=link.link_id,
        notebook_id=link.notebook_id,
        permission=link.permission,  # type: ignore[arg-type]
        use_current_user_credentials=True,
    )
