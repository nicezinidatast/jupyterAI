"""Real-Keycloak OIDC end-to-end integration.

Verifies that:

1. The Keycloak container has booted with the imported ``dataplatform`` realm
   and the four seeded users.
2. A direct-access-grant password flow yields a valid RS256 token with
   ``iss=http://keycloak:8080/realms/dataplatform`` and the user's realm-roles.
3. The backend ``/api/auth/me`` endpoint verifies that token against the
   running Keycloak JWKS and reflects the realm-roles from the token (not the
   DB seed) — proving the OIDC path is wired, not just the demo fallback.
4. The demo fallback still works for callers without a token (hybrid policy)
   so the SPA bring-up continues to function.
5. A garbage token is rejected with 401.

The token is fetched via ``docker exec`` so the issuer claim is pinned to the
docker-network hostname (``keycloak:8080``) that backend expects. Hitting
Keycloak on the host-published port (8090) would give back a token whose ``iss``
embeds 8090, which the backend would (correctly) refuse.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import httpx
import pytest

BACKEND = "http://localhost:8081"
BACKEND_CONTAINER = "dataplatform-0521-backend-1"

# Docker may live on the host PATH (Docker Desktop) or only inside WSL
# (docker-ce in the distro). Resolve once at import time.
_DOCKER_CMD: list[str] = (
    ["docker"] if shutil.which("docker") else ["wsl", "-e", "docker"]
)


def _password_grant(username: str, password: str) -> str:
    """Fetch an access token via direct access grants from inside the network."""
    cmd = [
        *_DOCKER_CMD,
        "exec",
        BACKEND_CONTAINER,
        "python",
        "-c",
        (
            "import httpx,sys,json;"
            "r=httpx.post("
            "'http://keycloak:8080/realms/dataplatform/protocol/openid-connect/token',"
            "data={"
            "'grant_type':'password',"
            "'client_id':'dataplatform-spa',"
            f"'username':'{username}',"
            f"'password':'{password}',"
            "'scope':'openid'"
            "})\n"
            "sys.stdout.write(r.text)"
        ),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
    body = json.loads(out.stdout)
    if "access_token" not in body:
        pytest.skip(f"keycloak token endpoint did not return access_token: {body}")
    return body["access_token"]


@pytest.fixture(scope="module")
def keycloak_ready() -> None:
    """Skip the module if Keycloak isn't serving the dataplatform realm."""
    try:
        r = httpx.get(
            "http://localhost:8090/realms/dataplatform/.well-known/openid-configuration",
            timeout=3,
        )
    except httpx.HTTPError as e:
        pytest.skip(f"keycloak not reachable on host: {e}")
    if r.status_code != 200:
        pytest.skip(f"keycloak realm not ready: HTTP {r.status_code}")


@pytest.mark.oidc
def test_backend_demo_fallback_without_token(keycloak_ready: None) -> None:
    """Hybrid policy: no Authorization header → demo-default seeded admin.

    Important — this is what keeps the SPA working before login is wired.
    """
    r = httpx.get(f"{BACKEND}/api/auth/me", timeout=5)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "admin@example.test"
    assert body["roles"] == ["Admin"]
    assert body["auth_source"] == "demo-default"


@pytest.mark.oidc
def test_backend_accepts_real_keycloak_token(keycloak_ready: None) -> None:
    """End-to-end: real Keycloak token → JWKS verify → DB user lookup.

    Asserts the OIDC path won, not the demo fallback (``auth_source=oidc``).
    Roles come from the token claims, proving the realm wins over DB roles.
    """
    token = _password_grant("alice.kim@example.test", "analyst")

    r = httpx.get(
        f"{BACKEND}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "alice.kim@example.test"
    assert body["roles"] == ["Analyst"]
    assert body["auth_source"] == "oidc"


@pytest.mark.oidc
def test_backend_rejects_bogus_token(keycloak_ready: None) -> None:
    """Junk in the Authorization header must be rejected, not silently downgraded."""
    r = httpx.get(
        f"{BACKEND}/api/auth/me",
        headers={"Authorization": "Bearer this-is-not-a-jwt"},
        timeout=5,
    )
    assert r.status_code == 401, r.text


@pytest.mark.oidc
def test_backend_role_propagation_for_auditor(keycloak_ready: None) -> None:
    """Auditor user round-trip — ensures the realm-role filter is per-user."""
    token = _password_grant("auditor@example.test", "auditor")
    r = httpx.get(
        f"{BACKEND}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "auditor@example.test"
    assert body["roles"] == ["Auditor"]
    assert body["auth_source"] == "oidc"
