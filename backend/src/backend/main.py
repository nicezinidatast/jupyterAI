"""Composite FastAPI app. Each unit contributes a router.

For the demo build we create tables directly via SQLAlchemy ``create_all``
on startup. Production swaps this out for ``alembic upgrade head`` driven
from an init container; see ``infra/ansible/site.yml`` for the wired path.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Response
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from admin_backend.api.router import router as admin_router
from admin_backend.models import Base as AdminBase
from backend.seed import seed_demo_data
from audit.api.router import router as audit_router
from audit.models import Base as AuditBase
from auth.api.oidc_dependency import OidcVerifier
from auth.api.router import router as auth_router
from auth.models import Base as AuthBase
from backend.config import BackendSettings
from credential.adapters.local_kms import LocalKmsAdapter
from credential.api.router import router as credential_router
from credential.models import Base as CredentialBase
from cryptography.fernet import Fernet
from data.api.router import router as data_router
from data.models import Base as DataBase
from dataplatform_shared.telemetry import (
    configure_logging,
    configure_tracing,
    get_logger,
    metrics_endpoint,
)
from copilot.api.router import router as copilot_router
from notebook.api.router import router as notebook_router
from notebook.models import Base as NotebookBase

logger = get_logger("backend.main")

_ALL_BASES = (AuthBase, AuditBase, CredentialBase, DataBase, NotebookBase, AdminBase)


async def _create_all_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for base in _ALL_BASES:
            await conn.run_sync(base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: BackendSettings = app.state.settings
    configure_logging(level=settings.log_level)
    configure_tracing(service_name="backend", otlp_endpoint=settings.otlp_endpoint or None)

    # pool_pre_ping: a pooled asyncpg connection can die behind our back
    # (postgres restart, idle timeout) — without the ping the next checkout
    # raises InterfaceError('connection is closed') as a user-facing 500.
    engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Fernet key for the local-KMS vault adapter. Empty config → generate a
    # process-scoped key (demo mode); production must inject a stable key.
    key_b = settings.credential_key.encode("utf-8") if settings.credential_key else Fernet.generate_key()
    app.state.vault_adapter = LocalKmsAdapter(
        key=key_b, session_factory=app.state.session_factory
    )

    if settings.oidc_issuer:
        app.state.oidc_verifier = OidcVerifier(
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience or None,
        )
        logger.info("oidc_verifier_ready", issuer=settings.oidc_issuer, strict=settings.oidc_strict)
    else:
        app.state.oidc_verifier = None
        logger.info("oidc_disabled_demo_mode")
    app.state.oidc_strict = settings.oidc_strict

    try:
        await _create_all_tables(engine)
        logger.info("backend_startup", database=settings.database_url.split("@")[-1])
        async with app.state.session_factory() as session:
            await seed_demo_data(session, vault_adapter=app.state.vault_adapter)
    except Exception as e:  # noqa: BLE001
        logger.error("startup_failed", error=str(e))
        # Keep serving /healthz so docker-compose health check still passes;
        # API endpoints that need the DB will fail at call time with 503.
    yield
    await engine.dispose()


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    settings = settings or BackendSettings()
    app = FastAPI(title="dataplatform backend", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(credential_router)
    app.include_router(data_router)
    app.include_router(notebook_router)
    app.include_router(admin_router)
    app.include_router(copilot_router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/metrics")
    async def metrics() -> Response:
        body, content_type = metrics_endpoint()
        return Response(content=body, media_type=content_type)

    @app.get("/")
    async def root() -> dict[str, object]:
        return {
            "service": "dataplatform-backend",
            "version": "0.1.0",
            "endpoints": [
                "/healthz",
                "/readyz",
                "/metrics",
                "/api/auth/me",
                "/api/audit/ping",
                "/api/credentials/ping",
                "/api/connections/ping",
                "/api/queries/ping",
                "/api/files/ping",
                "/api/notebooks/ping",
                "/api/share/ping",
                "/api/admin/ping",
            ],
        }

    return app


app = create_app()
