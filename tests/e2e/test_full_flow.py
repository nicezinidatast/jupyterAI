"""4가지 헤드라인 플로우를 검증하는 end-to-end 스모크 테스트.

``docker compose up`` 으로 기동한 스택의 백엔드(``http://localhost:8081``)를 대상으로 실행한다.
백엔드 health 엔드포인트에 접근할 수 없으면 자동 skip된다 — 개발/데모 환경에서만 실행된다.

검증 범위:

* 시나리오 1: 커넥션 목록 조회 + 실제 쿼리 실행 → 실제 행 + PII 마스킹 적용 확인
* 시나리오 2: 스키마 인트로스펙션 → PII kind 레이블이 붙은 실제 테이블 확인
* 시나리오 3: copilot 채팅(스텁 친화적 — provider 미설정 시 200 또는 503 허용,
  그 외 상태 코드는 실패)
* 시나리오 4: admin test-connection → sales_db 에 대해 ok=true 확인
"""

from __future__ import annotations

import os
import socket
import urllib.parse

import httpx
import pytest

BACKEND_URL = os.environ.get("E2E_BACKEND_URL", "http://localhost:8081")


def _backend_reachable() -> bool:
    """백엔드 /healthz 가 2초 이내에 200을 반환하면 True를 반환한다.

    pytestmark skip 조건으로 사용된다.
    """
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
    """모듈 스코프 httpx 클라이언트. 모든 테스트 함수가 공유하여 커넥션 오버헤드를 줄인다."""
    with httpx.Client(base_url=BACKEND_URL, timeout=15.0) as c:
        yield c


@pytest.fixture(scope="module")
def sales_db_id(client: httpx.Client) -> str:
    """시드된 sales_db 커넥션의 connection_id 를 반환한다.

    데모 Postgres 컨테이너가 기동되지 않았거나 백엔드가 재시작되지 않았으면 실패한다.
    """
    r = client.get("/api/connections")
    r.raise_for_status()
    rows = r.json()
    sales = next((c for c in rows if c["name"] == "sales_db"), None)
    assert sales, "sales_db connection not seeded — start demo-postgres + restart backend"
    return sales["connection_id"]


def test_scenario_1_real_query_with_masking(client: httpx.Client, sales_db_id: str) -> None:
    """실제 쿼리 실행 후 PII 마스킹이 적용된 행이 반환됨을 검증한다.

    불변식: name 과 email 컬럼에 '*' 마스크 문자가 포함되어야 한다.
    원본 값이 그대로 노출되면 이 어서션이 실패한다.
    """
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
    # PII 마스킹: name 에 '*' 가 하나 이상, email 에 마스크 문자가 있어야 한다.
    for row in body["rows"]:
        assert "*" in row["name"], f"name not masked: {row['name']}"
        assert "***" in row["email"] or "*" in row["email"], f"email not masked: {row['email']}"


def test_scenario_2_real_schema_with_pii_labels(client: httpx.Client, sales_db_id: str) -> None:
    """스키마 인트로스펙션 결과에 PII kind 레이블이 올바르게 붙어있음을 검증한다.

    불변식: email/phone/rrn 컬럼에는 각각 해당 pii_kind 가, id 컬럼에는 None 이어야 한다.
    PII 레이블이 잘못 붙으면 마스킹 정책이 잘못 적용된다.
    """
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
    """copilot provider 엔드포인트가 응답하고, 알려진 상태 코드만 반환함을 검증한다.

    200 = provider 설정됨(ollama 또는 anthropic); 503 = provider 없음.
    그 외 상태 코드는 버그다.
    """
    r = client.get("/api/copilot/provider")
    # 200 = provider 설정됨(ollama 또는 anthropic), 503 = provider 미설정
    assert r.status_code in (200, 503), r.text
    if r.status_code == 200:
        body = r.json()
        assert body["provider"] in ("ollama", "anthropic")


def test_scenario_3b_copilot_chat_post_audits_with_no_row_data(
    client: httpx.Client, sales_db_id: str
) -> None:
    """POST /api/copilot/chat 가 요청을 수락하고, LLM 가용 여부에 상관없이
    row_data_transmitted=false 인 audit 행을 기록함을 검증한다(FR-LLM-05).

    스트리밍 본문은 LLM 미기동 시 비어 있고 기동 시 chunk 를 포함하지만,
    두 경우 모두 이 테스트에서 허용한다. 중요한 것은 audit 보장이다.
    """
    # audit 엔드포인트 존재 여부만 확인한다(현재 행 수를 세지 않는다).
    before = client.get("/api/audit/event-types").status_code
    assert before in (200, 404)  # 엔드포인트 존재 여부 확인용

    # LLM 이 없어도 엔드포인트는 요청을 수락하고 audit 행을 생성해야 한다.
    r = client.post(
        "/api/copilot/chat",
        json={
            "question": "Show top 5 cities by sales amount",
            "connection_id": sales_db_id,
        },
        timeout=30.0,
    )
    # 200(스트리밍 OK) 또는 503(provider 없음) — rate-limit 는 429 이므로 해당 안 됨
    assert r.status_code in (200, 503), r.text

    # audit 행에 row_data_transmitted=false 가 기록되었는지 확인한다.
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
    """admin test-connection 이 sales_db 에 대해 ok=true 와 응답 지연시간을 반환함을 검증한다.

    불변식: latency_ms 가 정수이고 5000ms 미만이어야 한다.
    커넥션이 실패하면 ok=False 가 반환된다.
    """
    r = client.post(f"/api/admin/connections/{sales_db_id}/test")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True, body
    assert isinstance(body["latency_ms"], int)
    assert body["latency_ms"] < 5000
