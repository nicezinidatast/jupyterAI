"""Facade exposed to AdminConsole — re-uses domain services from sibling units."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class AdminService:
    """Façade — holds a session and forwards to the right unit's service."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # Concrete dependency wiring (auth/RoleResolver, data/PiiPolicyStore,
        # etc.) happens in the backend integration package so this class stays
        # free of cyclic imports.
