"""RDBMS connector skeleton.

Real driver wiring (asyncpg, pymysql, oracledb, pymssql) happens at integration
time. The MVP connector keeps the surface minimal so the DataAccessService can
be exercised end-to-end with the in-memory fake below.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from dataplatform_shared.security.secret import Secret

from data.connectors.base import Connector, ResultStream
from data.schemas import ConnectionSpec, ParamQuery


class _ListResultStream:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        for row in self._rows:
            yield row


class RdbmsConnector(Connector):
    """Skeleton connector. Tests inject ``_canned_rows`` for deterministic runs."""

    def __init__(self, spec: ConnectionSpec, secret: Secret) -> None:
        self._spec = spec
        self._secret = secret  # used by real driver wiring
        self._canned_rows: list[dict[str, Any]] = []

    def set_canned_rows(self, rows: list[dict[str, Any]]) -> None:
        """Test hook — production code calls a real driver instead."""
        self._canned_rows = rows

    async def execute(self, query: ParamQuery, *, timeout: float = 5.0) -> ResultStream:
        # Real implementation: choose driver based on engine, open connection
        # using ``self._secret.reveal()`` then call cursor.execute with paramstyle.
        # ``timeout`` is wired via driver-specific kwargs in production.
        del query, timeout
        return _ListResultStream(list(self._canned_rows))

    async def introspect(self, schema: str | None = None) -> dict[str, Any]:
        del schema
        return {"tables": []}

    async def close(self) -> None:
        # Real implementation closes the underlying connection.
        return None
