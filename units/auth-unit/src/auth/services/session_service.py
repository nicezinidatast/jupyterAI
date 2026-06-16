"""Opaque server-side session lifecycle.

A session is a row in the ``sessions`` table whose ``session_id`` (a UUID) is
handed to the browser verbatim as the value of the ``dp_session`` httpOnly
cookie. There is no JWT and nothing client-readable: revocation is a single
``UPDATE sessions SET invalidated_at = now()``.

Resolution order for an authenticated request is owned by
``auth.api.oidc_dependency``; this module only provides the primitives.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import Session as SessionRow
from auth.models import User, UserRole

# 7-day rolling session lifetime (contract default).
SESSION_TTL = timedelta(days=7)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def issue_session(db: AsyncSession, user_id: UUID) -> UUID:
    """Create a new session row for ``user_id`` and return its id (cookie value).

    The caller is responsible for committing the surrounding transaction.
    """
    now = _now()
    session_id = uuid4()
    db.add(
        SessionRow(
            session_id=session_id,
            user_id=user_id,
            issued_at=now,
            expires_at=now + SESSION_TTL,
            invalidated_at=None,
            last_seen_at=now,
        )
    )
    return session_id


def _coerce_session_id(raw: str | None) -> UUID | None:
    if not raw:
        return None
    try:
        return UUID(raw)
    except (ValueError, AttributeError):
        return None


async def resolve_session(
    db: AsyncSession, cookie_value: str | None
) -> tuple[User, list[str]] | None:
    """Resolve a ``dp_session`` cookie value to ``(User, roles)`` or ``None``.

    Returns ``None`` when the cookie is absent/malformed, the session row does
    not exist, is invalidated, or is past its expiry. Touches ``last_seen_at``
    on a successful resolve (best-effort; not committed here).
    """
    session_id = _coerce_session_id(cookie_value)
    if session_id is None:
        return None

    row = await db.get(SessionRow, session_id)
    if row is None or row.invalidated_at is not None:
        return None

    # expires_at is stored tz-aware on Postgres but may come back naive from
    # SQLite; normalise before comparing so the check is correct on both.
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= _now():
        return None

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None

    roles = [
        r.role
        for r in (
            await db.execute(select(UserRole).where(UserRole.user_id == user.user_id))
        ).scalars()
    ]

    # Best-effort recency update; the request's own transaction will commit it.
    row.last_seen_at = _now()
    return user, roles


async def invalidate_session(db: AsyncSession, cookie_value: str | None) -> bool:
    """Mark the session for ``cookie_value`` invalidated. Returns True if found."""
    session_id = _coerce_session_id(cookie_value)
    if session_id is None:
        return False
    row = await db.get(SessionRow, session_id)
    if row is None:
        return False
    if row.invalidated_at is None:
        row.invalidated_at = _now()
    return True
