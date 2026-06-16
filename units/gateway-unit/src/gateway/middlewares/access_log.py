"""Emit a structured access log per request (NFR-SEC-02)."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from dataplatform_shared.telemetry import REQUEST_COUNT, REQUEST_LATENCY, get_logger

logger = get_logger("gateway.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception:  # noqa: BLE001 — re-raised after logging
            status = 500
            raise
        finally:
            elapsed = time.perf_counter() - start
            route = request.url.path
            REQUEST_COUNT.labels(unit="gateway", route=route, method=request.method, code=str(status)).inc()
            REQUEST_LATENCY.labels(unit="gateway", route=route).observe(elapsed)
            logger.info(
                "request",
                method=request.method,
                path=route,
                status=status,
                latency_ms=int(elapsed * 1000),
            )
