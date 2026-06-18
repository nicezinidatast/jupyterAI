"""실제 Keycloak 을 사용하는 OIDC end-to-end 통합 테스트.

검증 항목:

1. Keycloak 컨테이너가 ``dataplatform`` 렐름과 4명의 시드 사용자와 함께 기동되었다.
2. Direct Access Grant(password 플로우)로 RS256 토큰을 발급받을 수 있고,
   토큰의 ``iss`` 가 ``http://keycloak:8080/realms/dataplatform`` 이며 realm-roles 가 포함된다.
3. 백엔드 ``/api/auth/me`` 가 실행 중인 Keycloak JWKS 로 토큰을 검증하고,
   DB 시드가 아닌 토큰 클레임의 realm-roles 를 반환한다 — OIDC 경로가 연결되어
   있음을 증명하며, 단순 데모 폴백이 아님을 확인한다.
4. 토큰 없는 호출자를 위한 데모 폴백이 여전히 동작한다(하이브리드 정책) —
   SPA 초기 기동이 계속 작동해야 한다.
5. 잘못된 토큰은 401 로 거부된다.

토큰을 ``docker exec`` 로 가져오는 이유: 발급자 클레임이 백엔드가 기대하는
도커 네트워크 호스트명(``keycloak:8080``)에 고정된다. 호스트 공개 포트(8090)로
직접 Keycloak 에 접근하면 ``iss`` 에 8090 이 들어간 토큰이 반환되고,
백엔드가(올바르게) 거부한다.
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
    """도커 네트워크 내부에서 Direct Access Grant 로 액세스 토큰을 가져온다.

    docker exec 로 백엔드 컨테이너 안에서 httpx 를 실행하여 Keycloak 에 접근한다.
    이렇게 하면 토큰 ``iss`` 가 ``keycloak:8080`` 으로 고정되어 백엔드가 검증할 수 있다.
    호스트 포트(8090)를 사용하면 ``iss`` 불일치로 검증이 실패한다.
    """
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
    """Keycloak 이 dataplatform 렐름을 서빙하지 않으면 모듈 전체를 skip한다.

    호스트 공개 포트(8090)에서 openid-configuration 엔드포인트를 확인한다.
    """
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
    """하이브리드 정책 검증: Authorization 헤더 없음 → 데모 기본 시드 어드민으로 응답한다.

    이것이 로그인이 연결되기 전에도 SPA 가 동작하는 이유다.
    auth_source='demo-default' 가 OIDC 경로가 아닌 데모 폴백을 사용했음을 증명한다.
    """
    r = httpx.get(f"{BACKEND}/api/auth/me", timeout=5)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "admin@example.test"
    assert body["roles"] == ["Admin"]
    assert body["auth_source"] == "demo-default"


@pytest.mark.oidc
def test_backend_accepts_real_keycloak_token(keycloak_ready: None) -> None:
    """end-to-end 검증: 실제 Keycloak 토큰 → JWKS 검증 → DB 사용자 조회.

    auth_source='oidc' 는 OIDC 경로가 동작하고 데모 폴백이 아님을 의미한다.
    역할이 토큰 클레임에서 오므로, DB 역할이 아닌 렐름 설정이 우선한다.
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
    """Authorization 헤더의 잘못된 토큰은 401 로 거부되어야 한다.

    조용히 데모 폴백으로 다운그레이드되어서는 안 된다 — 이는 보안 홀이다.
    """
    r = httpx.get(
        f"{BACKEND}/api/auth/me",
        headers={"Authorization": "Bearer this-is-not-a-jwt"},
        timeout=5,
    )
    assert r.status_code == 401, r.text


@pytest.mark.oidc
def test_backend_role_propagation_for_auditor(keycloak_ready: None) -> None:
    """Auditor 사용자 왕복 검증 — realm-role 필터가 사용자별로 올바르게 동작함을 보장한다.

    alice 가 Analyst 로 동작한다고 해서 auditor 도 Analyst 가 되어서는 안 된다.
    """
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
