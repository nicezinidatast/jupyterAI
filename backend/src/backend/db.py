"""FastAPI dependency that hands out an AsyncSession per request."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        factory = async_sessionmaker(request.app.state.engine, expire_on_commit=False)
        request.app.state.session_factory = factory
    return factory


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory = _session_factory(request)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
