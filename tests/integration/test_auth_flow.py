"""로컬 쿠키 세션 인증 플로우의 통합 테스트.

실제 복합 FastAPI 앱(모든 unit 라우터)을 in-process ASGI 트랜스포트로 구동하고,
신선한 파일 기반 SQLite DB 를 사용한다 — Docker 도, 네트워크도 필요 없다.

검증 범위: 어드민 부트스트랩 로그인, 자유 가입(id/password, 즉시 활성화, 자동 로그인),
중복·유효성 검사 거부, 대소문자 무시 id, 로그아웃, 미인증 401 경로.

이 디렉터리의 다른 postgres 통합 테스트와 달리 SQLite 를 사용하므로 어디서든 실행된다.
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
_DB_DIR = tempfile.mkdtemp(prefix="dp_auth_it_")
os.environ["BACKEND_DATABASE_URL"] = (
    f"sqlite+aiosqlite:///{(Path(_DB_DIR) / 'auth.db').as_posix()}"
)
os.environ["BACKEND_OIDC_ISSUER"] = ""  # keycloak 없음 — 쿠키/데모 인증만 사용
os.environ["BACKEND_SEED_DEMO"] = "false"
os.environ["BACKEND_COOKIE_SECURE"] = "false"


def test_auth_flow() -> None:
    """in-process ASGI 트랜스포트로 전체 인증 플로우를 검증하는 엔트리포인트."""
    asyncio.run(_run())


async def _run() -> None:
    """실제 FastAPI 앱을 SQLite 에 연결하고 인증 플로우 시나리오를 순서대로 실행한다.

    각 시나리오는 새 AsyncClient 를 생성해 쿠키 격리를 보장한다.
    """
    import httpx

    from backend.config import BackendSettings
    from backend.main import create_app, lifespan

    app = create_app(BackendSettings())
    async with lifespan(app):  # 테이블 생성 + admin 계정 부트스트랩
        transport = httpx.ASGITransport(app=app)

        def client() -> httpx.AsyncClient:
            return httpx.AsyncClient(transport=transport, base_url="http://t")

        # 1) admin(admin / admin_st) 로그인 → /me 에서 Admin 역할 확인 → 로그아웃 후 401
        async with client() as c:
            r = await c.post(
                "/api/auth/login", json={"username": "admin", "password": "admin_st"}
            )
            assert r.status_code == 200, (r.status_code, r.text)
            assert r.cookies.get("dp_session"), "login must set dp_session cookie"
            me = await c.get("/api/auth/me")
            assert me.status_code == 200, me.text
            assert "Admin" in me.json()["user"]["roles"], me.text
            assert (await c.post("/api/auth/logout")).status_code == 200
            assert (await c.get("/api/auth/check")).status_code == 401

        # 2) 잘못된 admin 비밀번호 → 401
        async with client() as c:
            r = await c.post(
                "/api/auth/login", json={"username": "admin", "password": "nope"}
            )
            assert r.status_code == 401, r.text

        # 3) 자유 가입(id + password) → 즉시 활성화, Analyst 역할로 자동 로그인
        async with client() as c:
            r = await c.post(
                "/api/auth/signup", json={"username": "tester1", "password": "1234"}
            )
            assert r.status_code == 200, (r.status_code, r.text)
            assert r.cookies.get("dp_session"), "signup must auto-login"
            assert r.json()["user"]["roles"] == ["Analyst"], r.text
            me = await c.get("/api/auth/me")
            assert me.status_code == 200 and me.json()["user"]["email"] == "tester1", me.text

        # 4) 중복 id → 409
        async with client() as c:
            r = await c.post(
                "/api/auth/signup", json={"username": "tester1", "password": "abcd"}
            )
            assert r.status_code == 409, r.text

        # 5) 유효성 검사: id 3-20자, password >= 4자 → 위반 시 422
        async with client() as c:
            assert (
                await c.post("/api/auth/signup", json={"username": "ab", "password": "1234"})
            ).status_code == 422
            assert (
                await c.post("/api/auth/signup", json={"username": "okname", "password": "123"})
            ).status_code == 422
            assert (
                await c.post("/api/auth/signup", json={"username": "x" * 21, "password": "1234"})
            ).status_code == 422

        # 6) 신규 사용자 로그인 가능, id 는 대소문자 무시
        async with client() as c:
            assert (
                await c.post("/api/auth/login", json={"username": "tester1", "password": "1234"})
            ).status_code == 200
            assert (
                await c.post("/api/auth/login", json={"username": "TESTER1", "password": "1234"})
            ).status_code == 200

        # 7) 쿠키 없음 → /me 와 /check 모두 401
        async with client() as c:
            assert (await c.get("/api/auth/me")).status_code == 401
            assert (await c.get("/api/auth/check")).status_code == 401
