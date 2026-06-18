"""HSTS·CSP·X-Frame-Options·X-Content-Type-Options·Referrer-Policy 헤더를 적용한다 (SECURITY-04).

브라우저 보안 헤더는 서버가 명시적으로 응답에 포함해야 효력이 있다.
미들웨어 하나로 모든 엔드포인트에 일괄 적용함으로써 라우터별 누락 위험을 없앤다.

각 헤더의 역할
--------------
- Strict-Transport-Security (HSTS): 브라우저가 이후 2년간 HTTPS만 사용하도록 강제.
  ``includeSubDomains``로 서브도메인까지 포함.
- X-Content-Type-Options: MIME 스니핑 방지. 선언된 Content-Type 그대로 해석.
- X-Frame-Options: 클릭재킹(clickjacking) 방어. 이 응답을 iframe에 넣지 못하도록.
- Referrer-Policy: 외부 링크 이동 시 Referer 헤더를 보내지 않아 URL 노출 방지.
- Content-Security-Policy (CSP): XSS 방어의 핵심.
  현재 'unsafe-inline'·'unsafe-eval'을 허용하는 이유는 JupyterLab이 인라인
  스크립트를 사용하기 때문이다. Phase 2에서 nonce 기반으로 강화할 예정.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# 모든 응답에 일괄 부착할 보안 헤더 집합.
# 모듈 수준 상수로 정의해 매 요청마다 딕셔너리를 재생성하지 않는다.
_HEADERS: dict[str, str] = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        # JupyterLab이 인라인 스크립트·스타일을 사용하므로 unsafe-inline·unsafe-eval 허용.
        # Phase 2에서 nonce 방식으로 전환해 CSP를 강화할 예정.
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """모든 HTTP 응답에 보안 헤더를 부착하는 미들웨어.

    ``setdefault``를 사용해 라우터·다른 미들웨어가 이미 헤더를 설정한 경우
    덮어쓰지 않는다. 이 미들웨어는 가장 안쪽(라우터 직전)에 위치해야 하며,
    그렇게 해야 응답 헤더가 생성된 직후 바로 부착된다.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for name, value in _HEADERS.items():
            response.headers.setdefault(name, value)
        return response
