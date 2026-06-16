"""Real PostgreSQL connector — backed by asyncpg.

Replaces the demo-only ``_fake_rows()`` path that previously synthesised query
results. Each ``execute`` call opens a short-lived connection (no pool in this
build — pools come with credential-unit refactor in RPS-05).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import asyncpg

from data.connectors.base import Connector, ResultStream
from data.schemas import ConnectionSpec, ParamQuery


class _RowStream:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        for row in self._rows:
            yield row

    def to_list(self) -> list[dict[str, Any]]:
        return list(self._rows)


class PostgresConnector(Connector):
    """Real asyncpg-backed connector.

    Username + password are passed in explicitly by the caller, which obtains
    the password by decrypting the Fernet ciphertext stored in
    :class:`credential.models.SecretsStorage` via the configured VaultAdapter.
    """

    def __init__(self, spec: ConnectionSpec, *, username: str, password: str) -> None:
        self._spec = spec
        self._username = username
        self._password = password

    async def _connect(self, timeout: float) -> asyncpg.Connection:
        return await asyncio.wait_for(
            asyncpg.connect(
                host=self._spec.host,
                port=self._spec.port,
                user=self._username,
                password=self._password,
                database=self._spec.database or "postgres",
            ),
            timeout=timeout,
        )

    async def execute(self, query: ParamQuery, *, timeout: float = 5.0) -> ResultStream:
        conn = await self._connect(timeout=timeout)
        try:
            rows = await asyncio.wait_for(conn.fetch(query.sql), timeout=timeout)
            dicts = [dict(r) for r in rows]
            return _RowStream(dicts)
        finally:
            await conn.close()

    async def introspect(self, schema: str | None = None) -> dict[str, Any]:
        target_schema = schema or "public"
        conn = await self._connect(timeout=5.0)
        try:
            table_rows = await conn.fetch(
                """
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_type = 'BASE TABLE'
                  AND table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
                """
            )
            column_rows = await conn.fetch(
                """
                SELECT table_schema, table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name, ordinal_position
                """
            )
        finally:
            await conn.close()

        tables: dict[tuple[str, str], list[dict[str, str]]] = {}
        for r in column_rows:
            tables.setdefault((r["table_schema"], r["table_name"]), []).append(
                {"name": r["column_name"], "type": r["data_type"]}
            )
        return {
            "schema": target_schema,
            "tables": [
                {
                    "schema": s,
                    "name": t,
                    "columns": tables.get((s, t), []),
                }
                for r in table_rows
                for (s, t) in [(r["table_schema"], r["table_name"])]
            ],
        }

    async def ping(self, *, timeout: float = 5.0) -> dict[str, Any]:
        conn = await self._connect(timeout=timeout)
        try:
            value = await conn.fetchval("SELECT 1")
            return {"ok": value == 1}
        finally:
            await conn.close()

    async def close(self) -> None:
        return None
