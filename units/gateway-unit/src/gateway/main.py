"""FastAPI app for the gateway. Owns the middleware stack and OIDC callback."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as aioredis
from fastapi import FastAPI

from dataplatform_shared.telemetry import (
    configure_logging,
    configure_tracing,
    get_logger,
)
from gateway.config import GatewaySettings
from gateway.middlewares.access_log import AccessLogMiddleware
from gateway.middlewares.rate_limit import RateLimitMiddleware
from gateway.middlewares.request_id import RequestIdMiddleware
from gateway.middlewares.security_headers import SecurityHeadersMiddleware
from gateway.routes import health, oidc

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: GatewaySettings = app.state.settings
    configure_logging(level=settings.log_level)
    configure_tracing(service_name="gateway-unit", otlp_endpoint=settings.otlp_endpoint or None)
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    logger.info("gateway_startup", backend=settings.backend_url)
    try:
        yield
    finally:
        await app.state.redis.close()
        logger.info("gateway_shutdown")


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    """Application factory — keeps tests free of singleton state."""
    settings = settings or GatewaySettings()

    app = FastAPI(title="dataplatform gateway", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    # Middleware order matters — outermost is applied first to the request.
    # Starlette processes them in REVERSE add order, so the last add is the
    # innermost. We add in the order we want them to run on the way in.
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(health.router)
    app.include_router(oidc.router)

    return app


app = create_app()
