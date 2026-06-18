"""첫 로그인 비밀번호 변경 안내 플래그(must_change_password) 통합 테스트.

분석 워크스페이스가 "초기 비밀번호를 변경하세요" 팝업을 띄울지 판단하는 신호인
``must_change_password``가 각 경로에서 올바르게 설정/해제되는지 검증한다.

- 관리자가 비밀번호를 정해 만든 계정: True (첫 로그인 시 변경 안내).
- 본인이 비밀번호를 변경하면: False (팝업 재노출 방지).
- 스스로 가입한 계정: 처음부터 False.
- 관리자 비밀번호 초기화: 다시 True.

``test_auth_flow.py``와 같은 in-process ASGI + SQLite 방식이라 Docker가 필요 없다.
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

_DB_DIR = tempfile.mkdtemp(prefix="dp_mustchange_it_")
os.environ["BACKEND_DATABASE_URL"] = (
    f"sqlite+aiosqlite:///{(Path(_DB_DIR) / 'mustchange.db').as_posix()}"
)
os.environ["BACKEND_OIDC_ISSUER"] = ""
os.environ["BACKEND_SEED_DEMO"] = "false"
os.environ["BACKEND_COOKIE_SECURE"] = "false"


def test_must_change_password_flag() -> None:
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

        # 1) 관리자가 비밀번호를 정해 사용자를 만든다 → 플래그 True 이어야 한다.
        async with client() as c:
            r = await c.post(
                "/api/admin/users",
                json={"email": "fred@corp.com", "roles": ["Analyst"], "password": "fred1234"},
            )
            assert r.status_code == 201, (r.status_code, r.text)
            fred_id = r.json()["user_id"]

        async with client() as c:
            r = await c.post("/api/auth/login", json={"username": "fred@corp.com", "password": "fred1234"})
            assert r.status_code == 200, r.text
            # 로그인 응답에도 플래그가 실려야 한다.
            assert r.json()["user"]["must_change_password"] is True, r.text
            me = await c.get("/api/auth/me")
            assert me.json()["user"]["must_change_password"] is True, me.text

            # 2) 본인이 비밀번호를 변경하면 플래그가 해제된다.
            ch = await c.post(
                "/api/auth/change-password",
                json={"current_password": "fred1234", "new_password": "fred5678"},
            )
            assert ch.status_code == 200, ch.text
            me2 = await c.get("/api/auth/me")
            assert me2.json()["user"]["must_change_password"] is False, me2.text

        # 3) 스스로 가입한 사용자는 처음부터 False.
        async with client() as c:
            r = await c.post("/api/auth/signup", json={"username": "gwen", "password": "gwen1234"})
            assert r.status_code == 200, r.text
            assert r.json()["user"]["must_change_password"] is False, r.text

        # 4) 관리자 비밀번호 초기화 → 다시 True.
        async with client() as c:
            assert (
                await c.put(f"/api/admin/users/{fred_id}/password", json={"password": "reset123"})
            ).status_code == 200
        async with client() as c:
            r = await c.post("/api/auth/login", json={"username": "fred@corp.com", "password": "reset123"})
            assert r.status_code == 200, r.text
            assert r.json()["user"]["must_change_password"] is True, r.text


if __name__ == "__main__":
    test_must_change_password_flag()
    print("OK: must_change_password flag regression test passed")
