"""비밀번호 관리 기능(관리자 초기화 + 본인 변경)의 통합 테스트.

``test_auth_flow.py``와 같은 방식으로, 실제 복합 FastAPI 앱(모든 unit 라우터)을
in-process ASGI 트랜스포트 + 파일 기반 SQLite로 구동한다 — Docker도 네트워크도 필요 없다.

검증 범위:
- 관리자 초기화: ``PUT /api/admin/users/{id}/password``로 비밀번호를 바꾸면 옛 비밀번호는
  막히고 새 비밀번호로 로그인된다(분실 계정 복구 경로).
- 본인 변경: ``POST /api/auth/change-password``는 현재 세션 쿠키로 본인을 식별하고,
  현재 비밀번호가 맞아야만 새 비밀번호로 교체한다. 변경 후 옛 비번은 막히고 새 비번은 통한다.
- 현재 비밀번호가 틀리면 400, 쿠키가 없으면 401.
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

_DB_DIR = tempfile.mkdtemp(prefix="dp_pwchange_it_")
os.environ["BACKEND_DATABASE_URL"] = (
    f"sqlite+aiosqlite:///{(Path(_DB_DIR) / 'pwchange.db').as_posix()}"
)
os.environ["BACKEND_OIDC_ISSUER"] = ""  # keycloak 없음 — 쿠키/데모 인증만 사용
os.environ["BACKEND_SEED_DEMO"] = "false"
os.environ["BACKEND_COOKIE_SECURE"] = "false"


def test_password_management() -> None:
    """관리자 초기화 + 본인 변경 전체 흐름을 검증하는 엔트리포인트."""
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

        # ── 관리자 비밀번호 초기화 ───────────────────────────────────────────
        # 1) 비밀번호와 함께 사용자를 만든다.
        async with client() as c:
            r = await c.post(
                "/api/admin/users",
                json={"email": "carol@corp.com", "roles": ["Analyst"], "password": "old12345"},
            )
            assert r.status_code == 201, (r.status_code, r.text)
            carol_id = r.json()["user_id"]

        # 2) 옛 비밀번호로 로그인되는 것을 먼저 확인한다.
        async with client() as c:
            assert (
                await c.post("/api/auth/login", json={"username": "carol@corp.com", "password": "old12345"})
            ).status_code == 200

        # 3) 관리자가 비밀번호를 초기화한다.
        async with client() as c:
            r = await c.put(f"/api/admin/users/{carol_id}/password", json={"password": "new12345"})
            assert r.status_code == 200, (r.status_code, r.text)

        # 4) 옛 비번은 막히고(401), 새 비번으로 로그인된다(200).
        async with client() as c:
            assert (
                await c.post("/api/auth/login", json={"username": "carol@corp.com", "password": "old12345"})
            ).status_code == 401
            assert (
                await c.post("/api/auth/login", json={"username": "carol@corp.com", "password": "new12345"})
            ).status_code == 200

        # ── 본인 비밀번호 변경 ───────────────────────────────────────────────
        # 5) 사용자를 만들고, 같은 클라이언트(쿠키 유지)로 로그인한다.
        async with client() as c:
            assert (
                await c.post(
                    "/api/admin/users",
                    json={"email": "dave@corp.com", "roles": ["Analyst"], "password": "dave1234"},
                )
            ).status_code == 201

        async with client() as c:
            assert (
                await c.post("/api/auth/login", json={"username": "dave@corp.com", "password": "dave1234"})
            ).status_code == 200

            # 6) 현재 비밀번호가 틀리면 400.
            r = await c.post(
                "/api/auth/change-password",
                json={"current_password": "wrongpw", "new_password": "dave5678"},
            )
            assert r.status_code == 400, (r.status_code, r.text)

            # 7) 현재 비밀번호가 맞으면 200으로 교체된다(같은 세션 유지).
            r = await c.post(
                "/api/auth/change-password",
                json={"current_password": "dave1234", "new_password": "dave5678"},
            )
            assert r.status_code == 200, (r.status_code, r.text)
            # 세션은 그대로 유효해야 한다(재로그인 강제 안 함).
            assert (await c.get("/api/auth/check")).status_code == 200

        # 8) 옛 비번은 막히고(401), 새 비번으로 로그인된다(200).
        async with client() as c:
            assert (
                await c.post("/api/auth/login", json={"username": "dave@corp.com", "password": "dave1234"})
            ).status_code == 401
            assert (
                await c.post("/api/auth/login", json={"username": "dave@corp.com", "password": "dave5678"})
            ).status_code == 200

        # 9) 쿠키(세션) 없이 변경 시도하면 401.
        async with client() as c:
            r = await c.post(
                "/api/auth/change-password",
                json={"current_password": "dave5678", "new_password": "whatever1"},
            )
            assert r.status_code == 401, (r.status_code, r.text)

        # ── 분실 계정 복구: 비번 없이 만든 사용자도 관리자 초기화로 살아난다 ──
        async with client() as c:
            r = await c.post("/api/admin/users", json={"email": "erin@corp.com", "roles": ["Viewer"]})
            assert r.status_code == 201, r.text
            erin_id = r.json()["user_id"]
        async with client() as c:
            assert (
                await c.post("/api/auth/login", json={"username": "erin@corp.com", "password": "x12345"})
            ).status_code == 401
        async with client() as c:
            assert (
                await c.put(f"/api/admin/users/{erin_id}/password", json={"password": "x12345"})
            ).status_code == 200
        async with client() as c:
            assert (
                await c.post("/api/auth/login", json={"username": "erin@corp.com", "password": "x12345"})
            ).status_code == 200


if __name__ == "__main__":
    test_password_management()
    print("OK: password management (admin reset + self change) regression test passed")
