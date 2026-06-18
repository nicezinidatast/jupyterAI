"""요청마다 구조적 접근 로그를 출력하고 Prometheus 메트릭을 기록한다 (NFR-SEC-02).

이 미들웨어는 미들웨어 체인의 가장 바깥쪽에 위치해야 한다.
그래야 실제 처리 시간(레이트 리밋·핸들러 포함 전체 경과)과 최종 상태 코드가
정확히 측정된다. 안쪽에 두면 이후 미들웨어의 오버헤드가 측정에서 빠진다.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from dataplatform_shared.telemetry import REQUEST_COUNT, REQUEST_LATENCY, get_logger

logger = get_logger("gateway.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """요청·응답 쌍마다 구조적 로그와 Prometheus 메트릭을 기록하는 미들웨어.

    예외가 발생해도 finally 블록이 반드시 실행되므로 로그·메트릭 누락이 없다.
    예외는 re-raise해 FastAPI 기본 예외 핸들러가 처리하게 한다.
    """

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
        except Exception:  # noqa: BLE001 — 로깅 후 반드시 재발생
            # 핸들러에서 처리되지 않은 예외: 상태 코드를 500으로 기록하고 그대로 던진다.
            status = 500
            raise
        finally:
            # 성공·실패 모두 여기서 메트릭과 로그를 기록한다.
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
