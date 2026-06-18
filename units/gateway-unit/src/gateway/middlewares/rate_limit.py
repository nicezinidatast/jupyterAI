"""Redis 슬라이딩 윈도우 방식의 IP별·사용자별 레이트 리밋 미들웨어.

두 단계 검사를 순서대로 수행한다:
1. **IP 기반 제한** — 인증 여부와 무관하게 항상 적용. DDoS·스캐닝 방어.
2. **사용자 기반 제한** — JWT 미들웨어가 X-Auth-User 헤더를 주입한 경우에만 추가 적용.
   인증된 사용자가 대량 자동화 요청을 보내는 상황을 억제한다.

Redis가 없으면(테스트 환경 등) 두 검사를 모두 건너뛰어 그대로 통과시킨다.
이 덕분에 레이트 리밋 없이도 단위 테스트가 동작하며, Redis 장애 시 서비스가
완전히 중단되지 않는다(Fail-Open 정책).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from dataplatform_shared.security.rate_limit import SlidingWindowLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP 또는 사용자 예산을 초과한 요청을 429로 거부하는 미들웨어.

    Redis가 ``app.state``에 연결되지 않은 경우(테스트 등) 요청을 그대로 통과시킨다.
    이는 의도된 Fail-Open 동작이다 — Redis 없이도 핵심 기능 테스트가 가능해야 하기 때문.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            # Redis 미연결 상태(테스트·데모) — 레이트 리밋 없이 통과.
            return await call_next(request)

        settings = request.app.state.settings
        client_ip = self._client_ip(request)

        # 1단계: IP 기반 슬라이딩 윈도우 검사
        ip_limiter = SlidingWindowLimiter(
            redis, limit=settings.rate_limit_per_ip_minute, window_seconds=60
        )
        if not await ip_limiter.check(f"rl:ip:{client_ip}"):
            return self._too_many("ip")

        # 2단계: 인증된 사용자 기반 검사.
        # X-Auth-User 헤더는 JWT 검증 미들웨어(MVP에서 미연결)가 설정한다.
        # 헤더가 없으면 사용자별 한도 검사를 건너뛴다.
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
        """실제 클라이언트 IP를 결정한다.

        Envoy·nginx 등 앞단 프록시가 있으면 X-Forwarded-For 헤더의 첫 번째 항목이
        원본 IP다. 쉼표 구분 목록에서 가장 왼쪽(신뢰 체인의 출발점)을 취한다.
        """
        if xff := request.headers.get("X-Forwarded-For"):
            return xff.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    @staticmethod
    def _too_many(scope: str) -> JSONResponse:
        """429 Too Many Requests 응답을 생성한다.

        ``Retry-After: 60`` 헤더를 포함해 클라이언트가 재시도 대기 시간을 알 수 있게 한다.
        ``scope`` 필드로 IP 한도 초과인지 사용자 한도 초과인지 구분한다.
        """
        return JSONResponse(
            {"error": "rate_limited", "scope": scope},
            status_code=429,
            headers={"Retry-After": "60"},
        )
