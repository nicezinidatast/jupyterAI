"""게이트웨이 FastAPI 앱. 미들웨어 스택 조립과 OIDC 콜백 라우팅을 담당한다.

이 모듈은 "앱 팩토리" 패턴을 사용한다. ``create_app()``이 설정을 받아
앱 인스턴스를 생성하므로, 테스트에서 설정을 주입해 싱글턴 전역 상태 오염 없이
독립적인 앱 인스턴스를 만들 수 있다.

미들웨어 적용 순서
------------------
Starlette는 ``add_middleware`` 호출 순서의 역순으로 미들웨어를 감싼다.
즉, 마지막에 추가한 미들웨어가 가장 안쪽(라우터에 가장 가까움)에 위치한다.
요청 흐름(안→밖)으로 보면 다음 순서가 된다:

1. SecurityHeadersMiddleware  (가장 안쪽 — 응답 헤더 부착)
2. RequestIdMiddleware        (상관 ID 발급·전파)
3. RateLimitMiddleware        (레이트 리밋 판정)
4. AccessLogMiddleware        (가장 바깥쪽 — 전체 요청/응답 로깅·메트릭)
"""

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
    """ASGI 라이프스팬 핸들러 — 앱 시작/종료 시 공유 자원을 초기화·정리한다.

    시작 시:
    - 구조적 로깅과 OpenTelemetry 트레이싱을 설정한다.
    - Redis 연결 풀을 생성해 ``app.state.redis``에 저장한다.
      이 핸들 은 RateLimitMiddleware가 요청마다 참조한다.

    종료 시 (finally 블록):
    - Redis 연결을 정상 종료해 소켓 누수를 방지한다.
    """
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
    """앱 팩토리 — 테스트가 싱글턴 상태에서 자유롭도록 매번 새 인스턴스를 반환한다.

    ``settings``를 생략하면 환경 변수에서 자동으로 읽어온다.
    테스트에서는 원하는 설정을 직접 전달해 Redis·백엔드 URL 등을 교체할 수 있다.
    """
    settings = settings or GatewaySettings()

    app = FastAPI(title="dataplatform gateway", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    # 미들웨어 순서 — Starlette는 add_middleware를 역순으로 감싸므로
    # "요청이 가장 먼저 만나야 하는" 미들웨어를 마지막에 추가한다.
    # 결과적인 요청 통과 순서(안→밖 = 추가 역순):
    #   SecurityHeaders → RequestId → RateLimit → AccessLog
    app.add_middleware(AccessLogMiddleware)   # 1번째 추가 = 가장 바깥쪽
    app.add_middleware(RateLimitMiddleware)   # 2번째 추가
    app.add_middleware(RequestIdMiddleware)   # 3번째 추가
    app.add_middleware(SecurityHeadersMiddleware)  # 4번째 추가 = 가장 안쪽

    app.include_router(health.router)
    app.include_router(oidc.router)

    return app


# 모듈 임포트 시 기본 인스턴스 생성. uvicorn은 이 심볼을 진입점으로 사용한다.
app = create_app()
