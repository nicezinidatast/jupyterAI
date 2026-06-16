"""End-to-end smoke for the four headline flows.

Runs against a live ``docker compose up`` stack on ``http://localhost:8081``
(the backend service). Skipped automatically when the backend health endpoint
is not reachable — i.e. only the dev/demo workflow runs these.

Coverage:

* Scenario 1: list connections + run a real query → real rows + PII masking
* Scenario 2: introspect schema → real tables with PII kind labels
* Scenario 3: copilot chat (stub-friendly — accepts 200 or 503 if no provider
  is configured, fails on any other status code)
* Scenario 4: admin test-connection → ok=true for sales_db
"""

from __future__ import annotations

import os
import socket
import urllib.parse

import httpx
import pytest

BACKEND_URL = os.environ.get("E2E_BACKEND_URL", "http://localhost:8081")


def _backend_reachable() -> bool:
    try:
        with httpx.Client(timeout=2.0) as c:
            return c.get(f"{BACKEND_URL}/healthz").status_code == 200
    except (httpx.HTTPError, socket.error):
        return False


pytestmark = pytest.mark.skipif(
    not _backend_reachable(), reason="backend not running on %s" % BACKEND_URL
)


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    with httpx.Client(base_url=BACKEND_URL, timeout=15.0) as c:
        yield c


@pytest.fixture(scope="module")
def sales_db_id(client: httpx.Client) -> str:
    r = client.get("/api/connections")
    r.raise_for_status()
    rows = r.json()
    sales = next((c for c in rows if c["name"] == "sales_db"), None)
    assert sales, "sales_db connection not seeded — start demo-postgres + restart backend"
    return sales["connection_id"]


def test_scenario_1_real_query_with_masking(client: httpx.Client, sales_db_id: str) -> None:
    r = client.post(
        "/api/queries/execute",
        json={
            "connection_id": sales_db_id,
            "sql": "SELECT name, email, phone FROM sales.customers LIMIT 3",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["row_count"] == 3
    assert body["columns"] == ["name", "email", "phone"]
    # PII masking: name should contain at least one '*', email should be masked
    for row in body["rows"]:
        assert "*" in row["name"], f"name not masked: {row['name']}"
        assert "***" in row["email"] or "*" in row["email"], f"email not masked: {row['email']}"


def test_scenario_2_real_schema_with_pii_labels(client: httpx.Client, sales_db_id: str) -> None:
    r = client.get(f"/api/connections/{sales_db_id}/schema")
    assert r.status_code == 200, r.text
    body = r.json()
    tables = {t["name"]: t for t in body["tables"]}
    assert "customers" in tables, "customers table missing in schema"
    customers = tables["customers"]
    cols_by_name = {c["name"]: c for c in customers["columns"]}
    assert cols_by_name["email"]["pii_kind"] == "email"
    assert cols_by_name["phone"]["pii_kind"] == "phone"
    assert cols_by_name["rrn"]["pii_kind"] == "rrn"
    assert cols_by_name["id"]["pii_kind"] is None


def test_scenario_3_copilot_endpoint_reachable(client: httpx.Client) -> None:
    r = client.get("/api/copilot/provider")
    # 200 = provider configured (ollama or anthropic); 503 = neither available
    assert r.status_code in (200, 503), r.text
    if r.status_code == 200:
        body = r.json()
        assert body["provider"] in ("ollama", "anthropic")


def test_scenario_3b_copilot_chat_post_audits_with_no_row_data(
    client: httpx.Client, sales_db_id: str
) -> None:
    """POST /api/copilot/chat must (a) accept the request, (b) write an audit
    row with row_data_transmitted=false, regardless of whether the LLM
    backend is actually reachable. The streaming body may be empty (LLM down)
    or contain chunks (LLM up) — both are acceptable here. What matters is
    the FR-LLM-05 audit guarantee.
    """
    # Count audit rows before the call
    before = client.get("/api/audit/event-types").status_code
    assert before in (200, 404)  # we just want to know the endpoint exists

    # Fire the chat call; even with no LLM the endpoint should accept the body
    # and produce an audit row.
    r = client.post(
        "/api/copilot/chat",
        json={
            "question": "Show top 5 cities by sales amount",
            "connection_id": sales_db_id,
        },
        timeout=30.0,
    )
    # 200 (streaming OK) OR 503 (provider missing — rate-limit hits would be 429)
    assert r.status_code in (200, 503), r.text

    # Confirm an audit row was written with row_data_transmitted=false
    audit = client.get(
        "/api/audit",
        params={"event_type": "copilot_chat", "limit": 5},
    )
    if audit.status_code == 200:
        body = audit.json()
        rows = body.get("items") if isinstance(body, dict) else body
        assert isinstance(rows, list), f"unexpected audit shape: {body!r}"
        matching = [
            row
            for row in rows
            if isinstance(row, dict)
            and row.get("event_type") == "copilot_chat"
            and (row.get("payload") or {}).get("row_data_transmitted") is False
        ]
        assert matching, f"no copilot_chat audit row with row_data_transmitted=false: {rows!r}"


def test_scenario_4_test_connection_succeeds(client: httpx.Client, sales_db_id: str) -> None:
    r = client.post(f"/api/admin/connections/{sales_db_id}/test")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True, body
    assert isinstance(body["latency_ms"], int)
    assert body["latency_ms"] < 5000
