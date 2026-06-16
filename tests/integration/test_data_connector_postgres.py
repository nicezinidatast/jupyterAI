"""Real-postgres integration for the data-unit PostgresConnector.

We seed a known schema directly with asyncpg, then exercise the connector's
``ping`` / ``execute`` / ``introspect`` against the actual driver path.
"""

from __future__ import annotations

import asyncpg
import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def seeded_db(asyncpg_dsn: str) -> str:
    """Create a minimal `customers` table the connector tests can rely on."""
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
    from data.connectors.postgres import PostgresConnector

    connector = PostgresConnector(spec_for_postgres, username="itest", password="itest")  # noqa: S106
    result = await connector.ping()
    assert result == {"ok": True}


async def test_execute_returns_real_rows(spec_for_postgres, seeded_db) -> None:
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
    """The connector intentionally lets driver errors bubble up — the caller
    layer (router) is responsible for turning them into 4xx responses.
    """
    from data.connectors.postgres import PostgresConnector
    from data.schemas import ParamQuery

    connector = PostgresConnector(spec_for_postgres, username="itest", password="itest")  # noqa: S106
    with pytest.raises(asyncpg.PostgresSyntaxError):
        await connector.execute(ParamQuery(sql="SELECT FROM WHERE"))
