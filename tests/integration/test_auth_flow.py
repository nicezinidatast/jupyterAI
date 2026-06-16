"""Integration test for the local cookie-session auth flow.

Drives the REAL composite FastAPI app (all unit routers) over an in-process
ASGI transport against a fresh file-backed SQLite DB — no docker, no network.
Covers: admin bootstrap login, free signup (id/password, active immediately,
auto-login), duplicate + validation rejection, case-insensitive id, logout, and
the unauthenticated 401 paths. Runs anywhere (SQLite), unlike the docker-gated
postgres integration tests in this directory.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# The shared conftest only wires a subset of unit srcs; add the rest needed to
# import the full composite app (auth / backend / admin / copilot / notebook /
# gateway), idempotently.
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

# Configure a throwaway SQLite DB + pure demo mode BEFORE importing the app.
_DB_DIR = tempfile.mkdtemp(prefix="dp_auth_it_")
os.environ["BACKEND_DATABASE_URL"] = (
    f"sqlite+aiosqlite:///{(Path(_DB_DIR) / 'auth.db').as_posix()}"
)
os.environ["BACKEND_OIDC_ISSUER"] = ""  # no keycloak — cookie/demo identity only
os.environ["BACKEND_SEED_DEMO"] = "false"
os.environ["BACKEND_COOKIE_SECURE"] = "false"


def test_auth_flow() -> None:
    asyncio.run(_run())


async def _run() -> None:
    import httpx

    from backend.config import BackendSettings
    from backend.main import create_app, lifespan

    app = create_app(BackendSettings())
    async with lifespan(app):  # creates tables + bootstraps the admin account
        transport = httpx.ASGITransport(app=app)

        def client() -> httpx.AsyncClient:
            return httpx.AsyncClient(transport=transport, base_url="http://t")

        # 1) admin (admin / admin_st) can log in; me shows Admin role; logout clears it
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

        # 2) wrong admin password -> 401
        async with client() as c:
            r = await c.post(
                "/api/auth/login", json={"username": "admin", "password": "nope"}
            )
            assert r.status_code == 401, r.text

        # 3) free signup (id + password) -> active immediately, auto-logged-in as Analyst
        async with client() as c:
            r = await c.post(
                "/api/auth/signup", json={"username": "tester1", "password": "1234"}
            )
            assert r.status_code == 200, (r.status_code, r.text)
            assert r.cookies.get("dp_session"), "signup must auto-login"
            assert r.json()["user"]["roles"] == ["Analyst"], r.text
            me = await c.get("/api/auth/me")
            assert me.status_code == 200 and me.json()["user"]["email"] == "tester1", me.text

        # 4) duplicate id -> 409
        async with client() as c:
            r = await c.post(
                "/api/auth/signup", json={"username": "tester1", "password": "abcd"}
            )
            assert r.status_code == 409, r.text

        # 5) validation: id 3-20 chars, password >= 4 -> 422 on violation
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

        # 6) the new user can log in; id is case-insensitive
        async with client() as c:
            assert (
                await c.post("/api/auth/login", json={"username": "tester1", "password": "1234"})
            ).status_code == 200
            assert (
                await c.post("/api/auth/login", json={"username": "TESTER1", "password": "1234"})
            ).status_code == 200

        # 7) no cookie -> me / check are 401
        async with client() as c:
            assert (await c.get("/api/auth/me")).status_code == 401
            assert (await c.get("/api/auth/check")).status_code == 401
