"""JupyterHub 연동용 platform-token 발급/검증 통합 테스트.

JupyterHub의 PlatformAuthenticator는 쿠키 없이 ``Authorization: Bearer <token>``으로
백엔드 ``/api/auth/me``를 호출해 사용자를 검증한다. 이 흐름이 동작하는지 확인한다:

1. 로그인한 사용자가 ``GET /api/auth/jupyter-token``으로 단기 토큰을 받는다(쿠키 인증).
2. 그 토큰을 Bearer로 ``/api/auth/me``에 보내면(쿠키 없이) 같은 사용자로 해석된다.
3. 잘못된 토큰/토큰 없음은 401.

``test_auth_flow.py``와 같은 in-process ASGI + SQLite 방식(Docker 불필요).
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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

_DB_DIR = tempfile.mkdtemp(prefix="dp_jupytoken_it_")
os.environ["BACKEND_DATABASE_URL"] = (
    f"sqlite+aiosqlite:///{(Path(_DB_DIR) / 'jupytoken.db').as_posix()}"
)
os.environ["BACKEND_OIDC_ISSUER"] = ""
os.environ["BACKEND_SEED_DEMO"] = "false"
os.environ["BACKEND_COOKIE_SECURE"] = "false"


def test_jupyter_token_bearer_flow() -> None:
    asyncio.run(_run())


async def _run() -> None:
    import httpx

    from backend.config import BackendSettings
    from backend.main import create_app, lifespan

    app = create_app(BackendSettings())
    async with lifespan(app):
        transport = httpx.ASGITransport(app=app)

        def client() -> httpx.AsyncClient:
            return httpx.AsyncClient(transport=transport, base_url="http://t")

        # 1) 가입(자동 로그인, 쿠키 설정) → jupyter-token 발급.
        async with client() as c:
            r = await c.post("/api/auth/signup", json={"username": "hubuser", "password": "hub1234"})
            assert r.status_code == 200, r.text
            tok = await c.get("/api/auth/jupyter-token")
            assert tok.status_code == 200, tok.text
            token = tok.json()["token"]
            assert token, "토큰이 비어 있으면 안 된다"

        # 2) 쿠키 없이 Bearer 토큰만으로 /me 가 같은 사용자로 해석되어야 한다(허브 인증자 경로).
        async with client() as c:
            me = await c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me.status_code == 200, me.text
            assert me.json()["user"]["email"] == "hubuser", me.text

        # 3) 잘못된 Bearer → 401.
        async with client() as c:
            bad = await c.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
            assert bad.status_code == 401, bad.text

        # 4) 쿠키도 Bearer도 없으면 401.
        async with client() as c:
            none = await c.get("/api/auth/me")
            assert none.status_code == 401, none.text

        # 5) 미인증 상태에서 jupyter-token 요청 → 401.
        async with client() as c:
            unauth = await c.get("/api/auth/jupyter-token")
            assert unauth.status_code == 401, unauth.text


if __name__ == "__main__":
    test_jupyter_token_bearer_flow()
    print("OK: jupyter-token + Bearer /me flow passed")
