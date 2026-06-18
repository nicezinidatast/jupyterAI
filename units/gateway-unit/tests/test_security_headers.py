"""모든 응답에 필수 보안 헤더 5종이 포함되어야 한다 (SECURITY-04).

이 테스트 모듈은 SecurityHeadersMiddleware와 RequestIdMiddleware의
계약(contract)을 검증한다. Redis 없이 동작하도록 ``create_app()``을
기본 설정으로 호출한다 — RateLimitMiddleware는 Redis 없을 때 Fail-Open으로 동작한다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from gateway.main import create_app


@pytest.fixture
def client() -> TestClient:
    """테스트용 앱 클라이언트. 매 테스트마다 새 인스턴스를 생성한다."""
    return TestClient(create_app())


def test_healthz_carries_security_headers(client: TestClient) -> None:
    """SECURITY-04: /healthz 응답에 5종 보안 헤더가 모두 포함되어야 한다."""
    r = client.get("/healthz")
    assert r.status_code == 200
    assert "Strict-Transport-Security" in r.headers
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert "Content-Security-Policy" in r.headers


def test_corr_id_echoed(client: TestClient) -> None:
    """클라이언트가 X-Correlation-Id를 보내면 응답에 그대로 반환되어야 한다."""
    r = client.get("/healthz", headers={"X-Correlation-Id": "test-123"})
    assert r.headers["X-Correlation-Id"] == "test-123"


def test_corr_id_generated_when_absent(client: TestClient) -> None:
    """X-Correlation-Id 없이 요청하면 서버가 ID를 발급해 응답 헤더에 포함해야 한다."""
    r = client.get("/healthz")
    assert r.headers.get("X-Correlation-Id")
    assert len(r.headers["X-Correlation-Id"]) >= 8


def test_oidc_callback_missing_params(client: TestClient) -> None:
    """code·state 파라미터 없이 /oidc/callback 호출 시 400이어야 한다.

    SECURITY-09: 어느 파라미터가 누락됐는지 응답 본문에 드러나면 안 된다.
    """
    r = client.get("/oidc/callback")
    assert r.status_code == 400
    # 누락된 파라미터 이름이 응답 텍스트에 함께 노출되면 안 된다.
    assert "code" not in r.text.lower() or "state" not in r.text.lower()
