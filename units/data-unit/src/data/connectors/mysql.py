"""실제 MySQL 커넥터 — aiomysql 기반.

``PostgresConnector``와 같은 구조를 따른다(엔진별 차이만 흡수). ``execute``는
호출마다 짧게 사는 커넥션을 열며, 풀링은 RPS-05의 credential-unit 리팩터와
함께 들어온다. MySQL 고유의 두 함정을 이 파일에서 흡수한다:
information_schema 컬럼명이 기본 대문자라는 점과, utf8mb4 인코딩 고정이다.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import aiomysql

from data.connectors.base import Connector, ResultStream
from data.schemas import ConnectionSpec, ParamQuery


def _lower_keys(row: dict[str, Any]) -> dict[str, Any]:
    # MySQL은 information_schema 컬럼명을 대문자로 돌려줄 수 있다. 결과 dict의
    # 키를 소문자로 정규화해, 상위 코드가 키 대소문자에 의존하지 않게 한다.
    return {k.lower(): v for k, v in row.items()}


class _RowStream:
    # aiomysql 결과 행을 ``ResultStream`` 모양으로 감싸는 어댑터(postgres.py와 동일).
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
        # charset=utf8mb4: 이모지·보조평면 문자까지 안전하게 다루기 위함.
        # DictCursor: 행을 dict로 받아 커넥터 계약(dict 스트림)과 맞춘다.
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
                # cur.description이 None이면 결과 집합이 없는 문장(예: DDL)이므로
                # fetchall을 호출하지 않고 빈 목록을 돌려준다.
                rows = list(await cur.fetchall()) if cur.description else []
            return _RowStream(rows)
        finally:
            conn.close()  # 예외와 무관하게 커넥션을 닫아 누수를 막는다

    async def introspect(self, schema: str | None = None) -> dict[str, Any]:
        # 스키마 미지정 시 접속 대상 DB를 조회 범위로 삼는다.
        target_schema = schema or self._spec.database
        conn = await self._connect(timeout=5.0)
        # MySQL은 기본적으로 information_schema 컬럼명을 대문자로 돌려준다.
        # SELECT에서 명시적으로 별칭(AS)을 붙여, 결과 dict 키가 예측 가능한
        # 소문자가 되도록 한다(_lower_keys와 함께 이중으로 안전장치).
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

        # (스키마, 테이블) 키로 컬럼을 묶는다. ordinal_position 순 조회라
        # append 순서가 곧 원래 컬럼 순서가 된다.
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
        # "연결 테스트" 프로브. SELECT 1로 접속·인증·왕복 여부만 확인한다.
        # DictCursor라 행이 dict이므로 첫 값(values()[0])이 1인지 본다.
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
