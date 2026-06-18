"""data-unit PostgresConnector 의 실제 postgres 통합 테스트.

asyncpg 로 알려진 스키마를 직접 시딩한 뒤, 커넥터의
``ping`` / ``execute`` / ``introspect`` 를 실제 드라이버 경로에 대해 검증한다.

검증 범위:
  - ping 이 ok=True 를 반환한다.
  - execute 가 삽입된 실제 행을 반환한다.
  - introspect 가 테이블과 컬럼 목록을 정확히 반환한다.
  - 잘못된 SQL 은 드라이버 예외를 버블업시킨다(라우터 계층이 4xx 로 변환).
"""

from __future__ import annotations

import asyncpg
import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def seeded_db(asyncpg_dsn: str) -> str:
    """커넥터 테스트가 의존할 최소 customers 테이블을 itest_sales 스키마에 생성한다.

    매번 DROP SCHEMA → CREATE SCHEMA 로 초기화하므로 이전 테스트 잔여 데이터가 없다.
    3개의 행(김민수, 이영희, 박지훈)이 시딩되어 execute 테스트가 예상 값을 확인할 수 있다.
    """
    conn = await asyncpg.connect(asyncpg_dsn)
    try:
        await conn.execute("DROP SCHEMA IF EXISTS itest_sales CASCADE")
        await conn.execute("CREATE SCHEMA itest_sales")
        await conn.execute(
            """
            CREATE TABLE itest_sales.customers (
                id        SERIAL PRIMARY KEY,
                name      TEXT NOT NULL,
                email     TEXT NOT NULL,
                phone     TEXT,
                city      TEXT
            )
            """
        )
        await conn.executemany(
            "INSERT INTO itest_sales.customers (name, email, phone, city) VALUES ($1,$2,$3,$4)",
            [
                ("김민수", "minsu@example.com", "010-1111-2222", "서울"),
                ("이영희", "younghee@example.com", "010-3333-4444", "부산"),
                ("박지훈", "jihoon@example.com", "010-5555-6666", "대구"),
            ],
        )
    finally:
        await conn.close()
    return asyncpg_dsn


async def test_ping_returns_ok(spec_for_postgres, seeded_db) -> None:
    """PostgresConnector.ping() 이 {"ok": True} 를 반환함을 검증한다.

    커넥션 자격증명과 DB 가용성을 확인하는 가장 기본적인 계약이다.
    """
    from data.connectors.postgres import PostgresConnector

    connector = PostgresConnector(spec_for_postgres, username="itest", password="itest")  # noqa: S106
    result = await connector.ping()
    assert result == {"ok": True}


async def test_execute_returns_real_rows(spec_for_postgres, seeded_db) -> None:
    """execute() 가 시딩된 실제 행을 올바른 순서로 반환함을 검증한다.

    id 기준 정렬로 시딩 순서와 반환 순서가 일치해야 한다.
    한글 이름이 올바르게 반환되는지도 확인한다.
    """
    from data.connectors.postgres import PostgresConnector
    from data.schemas import ParamQuery

    connector = PostgresConnector(spec_for_postgres, username="itest", password="itest")  # noqa: S106
    stream = await connector.execute(
        ParamQuery(sql="SELECT name, email, phone FROM itest_sales.customers ORDER BY id")
    )
    rows = stream.to_list()
    assert len(rows) == 3
    assert rows[0]["name"] == "김민수"
    assert rows[1]["email"] == "younghee@example.com"
    assert rows[2]["phone"] == "010-5555-6666"


async def test_introspect_lists_table_and_columns(spec_for_postgres, seeded_db) -> None:
    """introspect() 가 itest_sales.customers 테이블과 모든 컬럼을 반환함을 검증한다.

    PII 레이블링이나 마스킹 정책 적용의 선행 조건이 되는 스키마 메타데이터 경로다.
    email 컬럼의 타입이 'text' 로 정확히 반환되어야 한다.
    """
    from data.connectors.postgres import PostgresConnector

    connector = PostgresConnector(spec_for_postgres, username="itest", password="itest")  # noqa: S106
    schema = await connector.introspect()

    tables = {(t["schema"], t["name"]): t for t in schema["tables"]}
    assert ("itest_sales", "customers") in tables

    customers = tables[("itest_sales", "customers")]
    columns_by_name = {c["name"]: c for c in customers["columns"]}
    for expected in ("id", "name", "email", "phone", "city"):
        assert expected in columns_by_name, f"missing column {expected}"
    assert columns_by_name["email"]["type"] == "text"


async def test_invalid_sql_propagates(spec_for_postgres, seeded_db) -> None:
    """잘못된 SQL 이 드라이버 예외로 버블업됨을 검증한다.

    커넥터는 의도적으로 드라이버 오류를 직접 전파한다.
    오류를 HTTP 4xx 응답으로 변환하는 책임은 호출자 계층(라우터)에 있다.
    """
    from data.connectors.postgres import PostgresConnector
    from data.schemas import ParamQuery

    connector = PostgresConnector(spec_for_postgres, username="itest", password="itest")  # noqa: S106
    with pytest.raises(asyncpg.PostgresSyntaxError):
        await connector.execute(ParamQuery(sql="SELECT FROM WHERE"))
