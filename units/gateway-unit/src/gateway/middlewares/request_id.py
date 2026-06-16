"""Generate/propagate a correlation id and bind it into the logging context."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from dataplatform_shared.telemetry.logging import bind_corr_id


class RequestIdMiddleware(BaseHTTPMiddleware):
    HEADER = "X-Correlation-Id"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        corr_id = request.headers.get(self.HEADER) or str(uuid.uuid4())
        bind_corr_id(corr_id)
        request.state.corr_id = corr_id
        response = await call_next(request)
        response.headers[self.HEADER] = corr_id
        return response
