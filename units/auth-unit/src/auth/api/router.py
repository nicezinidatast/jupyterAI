"""auth-unit public API.

Identity is resolved through :func:`auth.api.oidc_dependency.get_current_identity`
which transparently supports two modes:

* **Demo mode** — when no OIDC issuer is configured, falls back to the
  seeded admin or to the ``X-User-Email`` header so the SPA bring-up works
  without Keycloak.
* **OIDC mode** — when Keycloak is wired in (``BACKEND_OIDC_ENABLED=true``),
  requires a valid Bearer token. The token's roles override the DB roles
  so the realm is the single source of truth.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.api.oidc_dependency import CurrentIdentity
from auth.models import User, UserRole
from backend.db import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/me")
async def me(
    session: Session,
    identity: CurrentIdentity,
) -> dict[str, object]:
    """Return the active user's profile.

    Roles come from the OIDC token when present; in demo mode they are
    resolved from the seeded DB rows.
    """
    user = (
        await session.execute(select(User).where(User.email == identity.email))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    if identity.roles:
        roles = list(identity.roles)
    else:
        roles = [
            r.role
            for r in (
                await session.execute(select(UserRole).where(UserRole.user_id == user.user_id))
            ).scalars()
        ]
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "display_name": user.display_name,
        "roles": sorted(roles),
        "is_active": user.is_active,
        "auth_source": identity.source,
    }
