"""Keycloak OIDC 엔드포인트를 감싸는 안티커럽션 계층(anti-corruption layer).

안티커럽션 계층은 외부 시스템의 모델·오류 형태가 우리 도메인으로 새어 들어오지
못하게 막는 경계다. Keycloak의 HTTP 응답·예외를 모두 우리 도메인 타입
(``KeycloakTokens``, ``DomainError``)으로 번역해, 호출자가 Keycloak이나 httpx의
세부 사항에 의존하지 않게 한다.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret


@dataclass(frozen=True, slots=True)
class KeycloakTokens:
    # 토큰들은 ``Secret``으로 감싼다 — 로그·repr에 우발적으로 평문이 찍히지 않게
    # 하기 위함이며, 값을 꺼내려면 명시적으로 ``.reveal()``을 호출해야 한다.
    access_token: Secret
    refresh_token: Secret
    id_token: Secret
    expires_in: int


class KeycloakAdapter:
    """Keycloak과 HTTP/JSON으로 통신한다. ``httpx.AsyncClient``는 테스트를 위해 주입한다.

    클라이언트를 생성자 주입(injection)으로 받는 이유는, 테스트에서 가짜 전송
    계층으로 바꿔 끼워 실제 네트워크 없이 응답을 흉내 낼 수 있게 하기 위함이다.
    모든 오류는 DomainError로 평탄화(flatten)되어, Keycloak 형태의 예외가 어댑터
    경계를 넘어 호출자에게 새지 않는다(Q-AD-10=A).
    """

    def __init__(
        self,
        *,
        issuer: str,
        client_id: str,
        client_secret: Secret,
        http: httpx.AsyncClient,
    ) -> None:
        self._issuer = issuer.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http

    async def exchange_auth_code(
        self, code: str, redirect_uri: str
    ) -> Result[KeycloakTokens, DomainError]:
        # 인가 코드(authorization code)를 토큰으로 교환하는 OAuth2 흐름. 네트워크
        # 장애와 HTTP 상태 코드를 각각 의미 있는 DomainError로 분류한다.
        try:
            r = await self._http.post(
                f"{self._issuer}/protocol/openid-connect/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret.reveal(),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
        except httpx.HTTPError:
            # 연결 실패·타임아웃 등 전송 계층 오류 → 외부 서비스 불가로 분류.
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        # 상태 코드별 분류: 400은 잘못된 코드/리다이렉트(클라이언트 입력 문제),
        # 5xx는 Keycloak 측 장애, 그 외 비-200은 인증 거부로 본다. 이 순서는
        # 더 구체적인 케이스(400, 5xx)를 먼저 걸러내기 위함이다.
        if r.status_code == 400:
            return Err(DomainError.VALIDATION)
        if r.status_code >= 500:
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        if r.status_code != 200:
            return Err(DomainError.UNAUTHORIZED)
        data = r.json()
        # refresh_token·expires_in은 없을 수 있어 기본값을 둔다. access_token·
        # id_token은 정상 응답에 반드시 있어야 하므로 키 누락 시 그대로 터지게 둔다.
        return Ok(
            KeycloakTokens(
                access_token=Secret(data["access_token"]),
                refresh_token=Secret(data.get("refresh_token", "")),
                id_token=Secret(data["id_token"]),
                expires_in=int(data.get("expires_in", 3600)),
            )
        )

    async def introspect(self, token: str) -> Result[dict, DomainError]:
        # 토큰 인트로스펙션(introspection): 토큰이 현재 유효한지 Keycloak에
        # 직접 물어본다. 로컬 서명 검증과 달리 즉시 폐기 여부까지 반영된다.
        try:
            r = await self._http.post(
                f"{self._issuer}/protocol/openid-connect/token/introspect",
                data={
                    "token": token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret.reveal(),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5.0,
            )
        except httpx.HTTPError:
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        if r.status_code != 200:
            return Err(DomainError.UNAUTHORIZED)
        body = r.json()
        # 인트로스펙션 응답의 ``active=false``는 토큰이 만료·폐기됐다는 뜻이다.
        # HTTP 200이라도 토큰 자체는 무효이므로 EXPIRED로 구분해 돌려준다.
        if not body.get("active"):
            return Err(DomainError.EXPIRED)
        return Ok(body)
