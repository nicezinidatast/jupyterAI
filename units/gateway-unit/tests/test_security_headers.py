"""Each response must carry the 5 required security headers (SECURITY-04)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from gateway.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_healthz_carries_security_headers(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert "Strict-Transport-Security" in r.headers
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert "Content-Security-Policy" in r.headers


def test_corr_id_echoed(client: TestClient) -> None:
    r = client.get("/healthz", headers={"X-Correlation-Id": "test-123"})
    assert r.headers["X-Correlation-Id"] == "test-123"


def test_corr_id_generated_when_absent(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.headers.get("X-Correlation-Id")
    assert len(r.headers["X-Correlation-Id"]) >= 8


def test_oidc_callback_missing_params(client: TestClient) -> None:
    r = client.get("/oidc/callback")
    assert r.status_code == 400
    # Should not leak which param was missing.
    assert "code" not in r.text.lower() or "state" not in r.text.lower()
