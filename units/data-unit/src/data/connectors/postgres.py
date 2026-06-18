"""실제 PostgreSQL 커넥터 — asyncpg 기반.

쿼리 결과를 지어내던 데모 전용 ``_fake_rows()`` 경로를 대체한다(실데이터로
동작해야 하므로). ``execute``는 호출마다 짧게 살아있는 커넥션을 연다. 이 빌드에는
풀(pool)이 없으며, 커넥션 풀링은 RPS-05의 credential-unit 리팩터와 함께 들어온다.
풀이 없으니 호출당 접속 비용이 있지만, 커넥션 수명 관리가 단순해진다는 트레이드오프다.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import asyncpg

from data.connectors.base import Connector, ResultStream
from data.schemas import ConnectionSpec, ParamQuery


class _RowStream:
    # asyncpg가 한 번에 가져온 행들을 ``ResultStream`` 모양으로 감싸는 어댑터.
    # ``to_list``를 함께 제공해, 스트림을 다 돌지 않고도 전체 목록을 받을 수 있다
    # (router가 hasattr로 ``to_list`` 유무를 보고 빠른 경로를 택한다).
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        for row in self._rows:
            yield row

    def to_list(self) -> list[dict[str, Any]]:
        return list(self._rows)


class PostgresConnector(Connector):
    """asyncpg 기반 실제 커넥터.

    사용자명·비밀번호는 호출부가 명시적으로 넘긴다. 호출부는 설정된
    VaultAdapter를 통해 :class:`credential.models.SecretsStorage`에 저장된
    Fernet 암호문을 복호화해 비밀번호를 얻는다. 이렇게 비밀번호를 인자로만
    받게 해, 커넥터 자체는 비밀 보관소(vault) 구현을 몰라도 되게 한다.
    """

    def __init__(self, spec: ConnectionSpec, *, username: str, password: str) -> None:
        self._spec = spec
        self._username = username
        self._password = password

    async def _connect(self, timeout: float) -> asyncpg.Connection:
        # 접속 자체에도 ``timeout``을 건다. 그렇지 않으면 응답 없는 호스트에서
        # 영원히 매달릴 수 있다. database가 비면 기본 'postgres'로 붙는다.
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
        # 접속과 fetch 양쪽에 timeout을 건다. finally에서 반드시 커넥션을 닫아
        # 예외가 나도 누수가 없게 한다(풀이 없으므로 직접 닫아야 한다).
        conn = await self._connect(timeout=timeout)
        try:
            rows = await asyncio.wait_for(conn.fetch(query.sql), timeout=timeout)
            dicts = [dict(r) for r in rows]
            return _RowStream(dicts)
        finally:
            await conn.close()

    async def introspect(self, schema: str | None = None) -> dict[str, Any]:
        # 스키마 미지정 시 'public'을 대상으로 본다. pg_catalog·information_schema
        # 같은 시스템 스키마는 제외해 사용자 테이블만 노출한다.
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

        # (스키마, 테이블) 키로 컬럼을 묶는다. 컬럼은 ordinal_position 순으로
        # 조회했으므로 append 순서가 곧 원래 컬럼 순서가 된다.
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
        # "연결 테스트" 프로브용. SELECT 1로 접속·인증·왕복이 모두 되는지만 확인한다.
        conn = await self._connect(timeout=timeout)
        try:
            value = await conn.fetchval("SELECT 1")
            return {"ok": value == 1}
        finally:
            await conn.close()

    async def close(self) -> None:
        return None
