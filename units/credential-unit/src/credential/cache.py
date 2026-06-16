"""Short-lived plaintext cache (TTL 60s by default).

We accept the small attack surface of an in-process cache in exchange for
avoiding a Vault round-trip on every query — Vault's audit log still records
the original ``read``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from uuid import UUID

from dataplatform_shared.security.secret import Secret


class ResolveCache:
    def __init__(self, *, ttl_seconds: int = 60) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._store: dict[UUID, tuple[Secret, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get_or_fetch(
        self, credential_id: UUID, fetcher: Callable[[], Awaitable[Secret]]
    ) -> Secret:
        now = datetime.utcnow()
        async with self._lock:
            entry = self._store.get(credential_id)
            if entry and entry[1] > now:
                return entry[0]
        secret = await fetcher()
        async with self._lock:
            self._store[credential_id] = (secret, now + self._ttl)
        return secret

    def invalidate(self, credential_id: UUID) -> None:
        self._store.pop(credential_id, None)
