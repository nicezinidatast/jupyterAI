"""Per-IP and per-user sliding-window rate limiting backed by Redis."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from dataplatform_shared.security.rate_limit import SlidingWindowLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests that exceed the per-IP or per-user budget.

    The middleware is permissive when Redis is not yet wired (tests):
    if ``request.app.state.redis`` is missing it simply forwards.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        settings = request.app.state.settings
        client_ip = self._client_ip(request)
        ip_limiter = SlidingWindowLimiter(
            redis, limit=settings.rate_limit_per_ip_minute, window_seconds=60
        )
        if not await ip_limiter.check(f"rl:ip:{client_ip}"):
            return self._too_many("ip")

        # Authenticated requests carry an X-Auth-User header set by the JWT
        # middleware (not yet wired into this MVP) — fall back to skipping the
        # user-limit if absent.
        user_id = request.headers.get("X-Auth-User")
        if user_id:
            u_limiter = SlidingWindowLimiter(
                redis, limit=settings.rate_limit_per_user_minute, window_seconds=60
            )
            if not await u_limiter.check(f"rl:user:{user_id}"):
                return self._too_many("user")

        return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str:
        # When behind another proxy, Envoy/nginx sets X-Forwarded-For.
        if xff := request.headers.get("X-Forwarded-For"):
            return xff.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    @staticmethod
    def _too_many(scope: str) -> JSONResponse:
        return JSONResponse(
            {"error": "rate_limited", "scope": scope},
            status_code=429,
            headers={"Retry-After": "60"},
        )
