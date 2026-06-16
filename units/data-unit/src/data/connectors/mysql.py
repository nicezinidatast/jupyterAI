"""Real MySQL connector — backed by aiomysql.

Mirrors PostgresConnector. Each ``execute`` opens a short-lived connection;
pooling lands with the credential-unit refactor in RPS-05.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import aiomysql

from data.connectors.base import Connector, ResultStream
from data.schemas import ConnectionSpec, ParamQuery


def _lower_keys(row: dict[str, Any]) -> dict[str, Any]:
    return {k.lower(): v for k, v in row.items()}


class _RowStream:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        for row in self._rows:
            yield row

    def to_list(self) -> list[dict[str, Any]]:
        return list(self._rows)


class MysqlConnector(Connector):
    def __init__(self, spec: ConnectionSpec, *, username: str, password: str) -> None:
        self._spec = spec
        self._username = username
        self._password = password

    async def _connect(self, timeout: float):
        return await aiomysql.connect(
            host=self._spec.host,
            port=self._spec.port,
            user=self._username,
            password=self._password,
            db=self._spec.database or None,
            connect_timeout=timeout,
            charset="utf8mb4",
            cursorclass=aiomysql.DictCursor,
        )

    async def execute(self, query: ParamQuery, *, timeout: float = 5.0) -> ResultStream:
        conn = await self._connect(timeout=timeout)
        try:
            async with conn.cursor() as cur:
                await asyncio.wait_for(cur.execute(query.sql), timeout=timeout)
                rows = list(await cur.fetchall()) if cur.description else []
            return _RowStream(rows)
        finally:
            conn.close()

    async def introspect(self, schema: str | None = None) -> dict[str, Any]:
        target_schema = schema or self._spec.database
        conn = await self._connect(timeout=5.0)
        # MySQL returns information_schema column names in UPPER case by default.
        # Alias them explicitly so the result dict has predictable lower-case keys.
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT table_schema AS table_schema,
                           table_name   AS table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                      AND table_schema = %s
                    ORDER BY table_schema, table_name
                    """,
                    (target_schema,),
                )
                table_rows = [_lower_keys(r) for r in await cur.fetchall()]
                await cur.execute(
                    """
                    SELECT table_schema AS table_schema,
                           table_name   AS table_name,
                           column_name  AS column_name,
                           data_type    AS data_type
                    FROM information_schema.columns
                    WHERE table_schema = %s
                    ORDER BY table_schema, table_name, ordinal_position
                    """,
                    (target_schema,),
                )
                column_rows = [_lower_keys(r) for r in await cur.fetchall()]
        finally:
            conn.close()

        tables: dict[tuple[str, str], list[dict[str, str]]] = {}
        for r in column_rows:
            tables.setdefault((r["table_schema"], r["table_name"]), []).append(
                {"name": r["column_name"], "type": r["data_type"]}
            )
        return {
            "schema": target_schema,
            "tables": [
                {
                    "schema": r["table_schema"],
                    "name": r["table_name"],
                    "columns": tables.get((r["table_schema"], r["table_name"]), []),
                }
                for r in table_rows
            ],
        }

    async def ping(self, *, timeout: float = 5.0) -> dict[str, Any]:
        conn = await self._connect(timeout=timeout)
        try:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                row = await cur.fetchone()
            return {"ok": bool(row) and list(row.values())[0] == 1}
        finally:
            conn.close()

    async def close(self) -> None:
        return None
