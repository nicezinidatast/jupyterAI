"""OIDC 콜백 핸들러 스켈레톤 — 실제 토큰 교환은 auth-unit에서 수행한다.

OIDC(OpenID Connect) 인가 코드 플로우에서 Keycloak이 사용자를 이 엔드포인트로
리다이렉트한다. 게이트웨이는 파라미터 존재 여부만 검증하고 토큰 교환을
auth-unit에 위임한다.

이 분리 구조의 이유:
- 토큰 교환·세션 발급 같은 보안에 민감한 로직을 auth-unit 한 곳에 집중시킨다.
- 게이트웨이를 얇게 유지해 공격 표면을 최소화한다.
- MVP에서는 ``${BACKEND_URL}/api/auth/callback``으로 프록시하고,
  통합 테스트가 리다이렉트 전체 생애주기를 검증한다.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from dataplatform_shared.telemetry import get_logger

router = APIRouter(prefix="/oidc")
logger = get_logger("gateway.oidc")


@router.get("/callback")
async def callback(request: Request, code: str | None = None, state: str | None = None) -> dict[str, str]:
    """OIDC 인가 코드를 수신하고 auth-unit에 처리를 넘긴다.

    ``code``와 ``state`` 중 하나라도 없으면 400을 반환한다.
    어느 파라미터가 빠졌는지는 응답에 포함하지 않는다(SECURITY-09).
    누락된 파라미터를 명시하면 공격자가 요청을 조작해 정보를 수집하는 데 이용할 수 있기 때문이다.

    정상 경로에서는 state만 로그에 기록하고 code는 기록하지 않는다.
    인가 코드는 민감한 일회성 자격증명이므로 로그에 남기면 안 된다.
    """
    if not code or not state:
        # 어느 파라미터가 없는지 노출하지 않는다 — 범용 메시지 사용 (SECURITY-09).
        raise HTTPException(status_code=400, detail="invalid_request")
    logger.info("oidc_callback_received", state=state)
    # auth-unit에 위임 — 세션 발급·리다이렉트는 §US-CODE-07에서 구현 예정.
    return {"received": "ok", "next": "auth-unit/exchange"}
