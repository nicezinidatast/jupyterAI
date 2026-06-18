"""어드민 콘솔로 만든 사용자가 실제로 로그인되는지 검증하는 통합 테스트.

이 테스트는 회귀(regression) 방지용이다. 과거 ``POST /api/admin/users``는 User 행을
만들 때 ``password_hash``를 채우지 않았고, 식별자를 정규화하지 않고 그대로 저장했다.
그 결과 어드민이 "신규 사용자 추가"로 만든 계정은 비밀번호 로그인이 항상 401로 실패했다.
(1) 비밀번호 해시가 없어 ``verify_password``가 항상 False였고, (2) 로그인은 식별자를
``strip().lower()``로 정규화해 조회하는데 저장값은 대문자가 섞여 있을 수 있었기 때문이다.

``test_auth_flow.py``와 같은 방식으로, 실제 복합 FastAPI 앱(모든 unit 라우터)을
in-process ASGI 트랜스포트 + 파일 기반 SQLite로 구동한다 — Docker도 네트워크도 필요 없다.

검증 범위:
- 어드민이 비밀번호와 함께 만든 사용자가 그 비밀번호로 로그인된다(세션 쿠키 발급).
- 로그인 아이디는 대소문자를 구분하지 않는다(저장 시 정규화됨).
- 틀린 비밀번호는 401.
- 비밀번호 없이 만든 사용자는 로컬 로그인이 거부된다(OIDC 전용 계약).
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 공유 conftest 는 unit src 의 일부만 등록한다. 전체 복합 앱
# (auth / backend / admin / copilot / notebook / gateway) 임포트에 필요한 나머지를
# 중복 없이(idempotently) 추가한다.
for _rel in (
    "units/shared-lib/src",
    "units/audit-unit/src",
    "units/auth-unit/src",
    "units/credential-unit/src",
    "units/data-unit/src",
    "units/notebook-unit/src",
    "units/gateway-unit/src",
    "units/copilot-unit/src",
    "units/admin-unit/backend/src",
    "backend/src",
):
    _p = str(ROOT / _rel)
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 앱 임포트 전에 임시 SQLite DB 와 순수 데모 모드를 설정한다.
# OIDC_ISSUER 를 비우면 Keycloak 없이 쿠키/데모 인증만 사용한다.
_DB_DIR = tempfile.mkdtemp(prefix="dp_admin_login_it_")
os.environ["BACKEND_DATABASE_URL"] = (
    f"sqlite+aiosqlite:///{(Path(_DB_DIR) / 'admin_login.db').as_posix()}"
)
os.environ["BACKEND_OIDC_ISSUER"] = ""  # keycloak 없음 — 쿠키/데모 인증만 사용
os.environ["BACKEND_SEED_DEMO"] = "false"
os.environ["BACKEND_COOKIE_SECURE"] = "false"


def test_admin_created_user_can_login() -> None:
    """어드민이 만든 사용자가 로그인되는 전체 흐름을 검증하는 엔트리포인트."""
    asyncio.run(_run())


async def _run() -> None:
    import httpx

    from backend.config import BackendSettings
    from backend.main import create_app, lifespan

    app = create_app(BackendSettings())
    async with lifespan(app):  # 테이블 생성 + admin 계정 부트스트랩
        transport = httpx.ASGITransport(app=app)

        def client() -> httpx.AsyncClient:
            return httpx.AsyncClient(transport=transport, base_url="http://t")

        # 1) 어드민이 비밀번호와 함께 사용자를 생성한다. 일부러 대문자를 섞어
        #    식별자 정규화가 동작하는지 함께 검증한다.
        async with client() as c:
            r = await c.post(
                "/api/admin/users",
                json={
                    "email": "Alice@Corp.com",
                    "display_name": "Alice",
                    "roles": ["Analyst"],
                    "password": "secret123",
                },
            )
            assert r.status_code == 201, (r.status_code, r.text)
            # 저장된 식별자는 소문자로 정규화되어 있어야 한다.
            assert r.json()["email"] == "alice@corp.com", r.text

        # 2) 그 비밀번호로 로그인되고 세션 쿠키가 발급된다(핵심 회귀 검증).
        async with client() as c:
            r = await c.post(
                "/api/auth/login",
                json={"username": "alice@corp.com", "password": "secret123"},
            )
            assert r.status_code == 200, (r.status_code, r.text)
            assert r.cookies.get("dp_session"), "login must set dp_session cookie"
            me = await c.get("/api/auth/me")
            assert me.status_code == 200, me.text
            assert "Analyst" in me.json()["user"]["roles"], me.text

        # 3) 로그인 아이디는 대소문자를 구분하지 않는다(원래 입력 그대로 쳐도 통과).
        async with client() as c:
            r = await c.post(
                "/api/auth/login",
                json={"username": "ALICE@CORP.COM", "password": "secret123"},
            )
            assert r.status_code == 200, (r.status_code, r.text)

        # 4) 틀린 비밀번호는 401.
        async with client() as c:
            r = await c.post(
                "/api/auth/login",
                json={"username": "alice@corp.com", "password": "nope"},
            )
            assert r.status_code == 401, r.text

        # 5) 비밀번호 없이 만든 사용자는 로컬 비밀번호 로그인이 거부된다(OIDC 전용 계약).
        async with client() as c:
            r = await c.post(
                "/api/admin/users",
                json={"email": "bob@corp.com", "roles": ["Viewer"]},
            )
            assert r.status_code == 201, r.text
        async with client() as c:
            r = await c.post(
                "/api/auth/login",
                json={"username": "bob@corp.com", "password": "whatever"},
            )
            assert r.status_code == 401, r.text


if __name__ == "__main__":
    test_admin_created_user_can_login()
    print("OK: admin-created user login regression test passed")
