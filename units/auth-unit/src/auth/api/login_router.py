"""Local authentication endpoints (signup / login / logout / me / check).

Free signup: a user picks an id (아이디) + password and is active immediately
(no email verification). These implement the shared cookie-session contract:

* the server sets an httpOnly cookie ``dp_session`` (value = opaque session id);
* ``SameSite=Lax; Path=/; HttpOnly`` (Secure gated behind ``BACKEND_COOKIE_SECURE``);
* the browser auto-sends it to same-origin ``/api`` and ``/jupyter`` so SPAs do
  not attach Authorization headers.

The identifier is a username (3-20 chars), stored in the ``User.email`` column
(which is just a unique string key — the admin account uses the literal
``"admin"`` there too). A freshly-created user defaults to role ``Analyst``.
The admin account is bootstrapped separately (see ``backend.seed.bootstrap_admin``).
"""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.api.oidc_dependency import SESSION_COOKIE
from auth.models import User, UserRole
from auth.services.password import hash_password, verify_password
from auth.services.session_service import (
    SESSION_TTL,
    invalidate_session,
    issue_session,
    resolve_session,
)
from backend.db import get_session
from dataplatform_shared.telemetry import get_logger

logger = get_logger("auth.login")

router = APIRouter()
Session = Annotated[AsyncSession, Depends(get_session)]

DEFAULT_ROLE = "Analyst"
# Usernames: 3-20 chars, letters/digits and a few safe separators.
USERNAME_PATTERN = r"^[A-Za-z0-9_.-]{3,20}$"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class SignupBody(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=4, max_length=72)  # >=4; bcrypt's 72-byte cap


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    email: str  # holds the username (kept as ``email`` for client compatibility)
    display_name: str | None
    roles: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalize_username(username: str) -> str:
    return username.strip().lower()


async def _roles_for(db: AsyncSession, user: User) -> list[str]:
    rows = (
        await db.execute(select(UserRole).where(UserRole.user_id == user.user_id))
    ).scalars()
    return sorted(r.role for r in rows)


def _cookie_secure(request: Request) -> bool:
    settings = getattr(request.app.state, "settings", None)
    return bool(getattr(settings, "cookie_secure", False))


def _set_session_cookie(response: Response, request: Request, session_id) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=str(session_id),
        max_age=int(SESSION_TTL.total_seconds()),
        path="/",
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(request),
    )


def _user_payload(user: User, roles: list[str]) -> dict[str, object]:
    return {
        "user": UserOut(
            email=user.email, display_name=user.display_name, roles=sorted(roles)
        ).model_dump()
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/signup")
async def signup(
    body: SignupBody, db: Session, request: Request, response: Response
) -> dict[str, object]:
    """Register a new account (active immediately) and start a session.

    409 if the username is already taken. The new user defaults to role
    ``Analyst`` and is logged in right away (``dp_session`` cookie set).
    """
    username = _normalize_username(body.username)
    existing = (
        await db.execute(select(User).where(User.email == username))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="exists")

    user = User(
        user_id=uuid4(),
        email=username,
        display_name=username,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    db.add(UserRole(user_id=user.user_id, role=DEFAULT_ROLE))
    session_id = await issue_session(db, user.user_id)
    await db.commit()

    _set_session_cookie(response, request, session_id)
    logger.info("auth_signup", username=username)
    return _user_payload(user, [DEFAULT_ROLE])


@router.post("/login")
async def login(
    body: LoginBody, db: Session, request: Request, response: Response
) -> dict[str, object]:
    """Password login. Sets ``dp_session`` on success.

    401 ``invalid_credentials`` — unknown id or wrong password.
    """
    username = _normalize_username(body.username)
    user = (
        await db.execute(select(User).where(User.email == username))
    ).scalar_one_or_none()

    if (
        user is None
        or not user.is_active
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="invalid_credentials")

    session_id = await issue_session(db, user.user_id)
    await db.commit()

    _set_session_cookie(response, request, session_id)
    roles = await _roles_for(db, user)
    logger.info("auth_login", username=username)
    return _user_payload(user, roles)


@router.post("/logout")
async def logout(
    db: Session,
    request: Request,
    response: Response,
) -> dict[str, bool]:
    """Invalidate the current session row and clear the cookie."""
    cookie_value = request.cookies.get(SESSION_COOKIE)
    await invalidate_session(db, cookie_value)
    await db.commit()
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
async def me(db: Session, request: Request) -> dict[str, object]:
    """Return the active user's profile, or 401 if the cookie does not resolve."""
    cookie_value = request.cookies.get(SESSION_COOKIE)
    resolved = await resolve_session(db, cookie_value)
    if resolved is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    user, roles = resolved
    await db.commit()  # persist last_seen_at touch
    return _user_payload(user, roles)


@router.get("/check")
async def check(db: Session, request: Request) -> dict[str, object]:
    """Lightweight authed probe: 200 ``{}`` when authed, 401 otherwise."""
    cookie_value = request.cookies.get(SESSION_COOKIE)
    resolved = await resolve_session(db, cookie_value)
    if resolved is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    await db.commit()
    return {}
