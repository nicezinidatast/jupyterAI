"""상관 ID(correlation ID)를 발급·전파하고 로깅 컨텍스트에 바인딩한다.

분산 추적 시나리오에서 클라이언트(또는 프록시)가 이미 X-Correlation-Id 헤더를
첨부했다면 그 값을 재사용해 서비스 간 요청을 하나의 트레이스로 엮는다.
헤더가 없으면 새 UUID v4를 발급해 모든 하위 요청에 전달한다.

ID는 세 곳에 저장된다:
- 구조적 로거 컨텍스트 (bind_corr_id): 이 요청의 모든 로그 라인에 자동 포함
- request.state.corr_id: 핸들러·다른 미들웨어가 ID를 직접 참조할 수 있도록
- 응답 헤더(X-Correlation-Id): 클라이언트가 서버 로그와 요청을 대조할 수 있도록
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from dataplatform_shared.telemetry.logging import bind_corr_id


class RequestIdMiddleware(BaseHTTPMiddleware):
    """X-Correlation-Id 헤더를 발급하거나 전파하는 미들웨어."""

    # 표준 상관 ID 헤더명. 인프라(nginx·Envoy·클라이언트)와 동일한 이름을 사용해야 한다.
    HEADER = "X-Correlation-Id"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 업스트림이 ID를 제공했으면 그대로 쓰고, 없으면 새로 발급한다.
        corr_id = request.headers.get(self.HEADER) or str(uuid.uuid4())
        bind_corr_id(corr_id)           # 로거 컨텍스트에 바인딩
        request.state.corr_id = corr_id  # 핸들러에서 직접 참조 가능하도록 저장
        response = await call_next(request)
        # 응답에도 ID를 포함시켜 클라이언트가 로그 추적에 사용할 수 있게 한다.
        response.headers[self.HEADER] = corr_id
        return response
