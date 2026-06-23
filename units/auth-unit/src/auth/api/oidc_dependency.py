"""인증된 사용자를 해석하는 FastAPI 의존성(dependency).

OIDC(OpenID Connect, OAuth2 위에 신원 계층을 얹은 표준)를 쓰는 환경과 그렇지
않은 개발/테스트 환경을 하나의 의존성으로 모두 지원한다. 두 모드를 별도 함수로
나누지 않는 이유는, 같은 엔드포인트가 환경 설정만 바꿔도 그대로 동작하게 해
배포 형상별로 라우팅을 분기하지 않기 위함이다.

* **데모 모드**(``settings.oidc_enabled=False``) — ``X-User-Email`` 헤더(개발·
  테스트에서 주입)나 시드된 admin 사용자로 폴백한다. Keycloak 없이도 SPA(단일
  페이지 앱) 초기 구동이 되도록 과거 동작을 보존한다.
* **OIDC 모드**(``settings.oidc_enabled=True``) — ``Authorization`` 헤더의
  Bearer 토큰을 요구한다. 토큰은 Keycloak의 JWKS(JSON Web Key Set, 서명 검증용
  공개키 묶음)로 RS256(RSA+SHA-256 서명) 검증하고, issuer(발급자) 클레임을
  ``settings.oidc_issuer``와 대조한다. 해석된 신원은 토큰 클레임의 이메일과
  realm-role(영역 역할)을 담는다.

전파되는 역할은 표준 플랫폼 역할 4종(Admin / Analyst / Auditor / Viewer)뿐이다.
토큰에 그 밖의 realm-role이 있어도 버린다 — Keycloak 쪽 오타나 잘못된 역할
부여가 권한을 의도치 않게 넓히지 못하도록 하는 안전장치(allow-list 방식)다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from jwt import PyJWKClient

# 토큰·세션에서 들어온 역할 중 이 집합에 속한 것만 신뢰한다(allow-list).
_PLATFORM_ROLES = frozenset({"Admin", "Analyst", "Auditor", "Viewer"})

# 서버가 설정하는 httpOnly 세션 쿠키 이름(여러 단위가 공유하는 계약). 브라우저가
# 동일 출처(same-origin)의 /api·/jupyter 요청에 자동으로 실어 보내므로, SPA는
# 일반 요청에 Authorization 헤더를 따로 붙일 필요가 없다.
SESSION_COOKIE = "dp_session"


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    """해석된 요청 신원. ``source``는 어떤 경로로 인증됐는지 알려주는 참고용이다."""

    email: str
    roles: tuple[str, ...]
    source: str  # "oidc" | "demo-header" | "demo-default"


class OidcVerifier:
    """서명 키를 캐싱하는 ``PyJWKClient`` 얇은 래퍼(wrapper).

    검증 실패는 종류를 가리지 않고 :class:`jwt.PyJWTError`로 던진다. 의존성은
    이를 일반화된 본문의 401로 바꿔, 어떤 검증이 실패했는지(만료/서명 불일치/
    issuer 불일치 등)를 클라이언트에 흘리지 않는다(SECURITY-09). 실패 원인을
    구체적으로 알려주면 공격자에게 단서를 주기 때문이다.
    """

    def __init__(self, *, issuer: str, audience: str | None = None) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience or None
        # ``cache_keys=True``(기본값)는 kid(key id, 서명 키 식별자)별로 키를
        # 캐싱한다. 따라서 첫 JWKS GET 이후의 검증은 네트워크 없이 메모리에서
        # 처리되어 매 요청마다 Keycloak을 때리지 않는다.
        self._jwks = PyJWKClient(
            f"{self.issuer}/protocol/openid-connect/certs",
            cache_keys=True,
        )

    def verify(self, token: str) -> dict[str, object]:
        # 토큰 헤더의 kid로 맞는 공개키를 골라 RS256 서명을 검증한다. issuer는
        # 반드시 일치해야 하고, audience(대상자)는 설정됐을 때만 검사한다.
        # ``require``로 iss·exp 클레임이 없으면 거부해 만료 없는 토큰을 막는다.
        signing_key = self._jwks.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=self.issuer,
            audience=self.audience,
            options={
                "verify_aud": self.audience is not None,
                "require": ["iss", "exp"],
            },
        )


def _roles_from_claims(claims: dict[str, object]) -> tuple[str, ...]:
    # Keycloak 토큰의 realm_access.roles에서 역할을 뽑는다. 토큰 구조를 신뢰하지
    # 않고 매 단계 타입을 확인한다 — 누락·형변형 시 빈 튜플로 안전하게 떨어뜨려
    # 권한 없는 신원으로 처리한다(fail-closed). 표준 역할만 통과시키고 정렬해
    # 결과가 결정적(deterministic)이도록 한다.
    realm_access = claims.get("realm_access") or {}
    if not isinstance(realm_access, dict):
        return ()
    roles = realm_access.get("roles") or []
    if not isinstance(roles, list):
        return ()
    return tuple(sorted(r for r in roles if isinstance(r, str) and r in _PLATFORM_ROLES))


def _demo_identity(x_user_email: str | None) -> AuthIdentity:
    # 데모 모드 폴백: 헤더가 있으면 그 이메일로, 없으면 시드된 admin으로 신원을
    # 만든다. 역할은 비워 두며(권한 검사는 상위에서 별도 처리), OIDC가 꺼진
    # 개발·테스트 구동에서만 쓰인다.
    if x_user_email:
        return AuthIdentity(email=x_user_email, roles=(), source="demo-header")
    return AuthIdentity(email="admin@example.test", roles=(), source="demo-default")


async def _identity_from_session_cookie(
    request: Request, cookie_value: str | None
) -> AuthIdentity | None:
    """``dp_session`` 쿠키를 신원으로 해석하거나 ``None``을 반환한다.

    앱의 세션 팩토리(session_factory)를 직접 써서 DB 세션을 연다 — 그래야 모든
    엔드포인트 시그니처가 인증만을 위해 DB 세션 인자를 끌고 다니지 않아도 된다.
    resolve_session은 지연 임포트(lazy import)한다: 모듈 최상단에서 임포트하면
    session_service → models → … → 이 모듈로 이어지는 순환 임포트가 생기기
    때문이다.
    """
    if not cookie_value:
        return None
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        return None
    from auth.services.session_service import resolve_session

    async with factory() as db:
        resolved = await resolve_session(db, cookie_value)
        if resolved is None:
            return None
        user, roles = resolved
        # resolve_session이 갱신한 last_seen_at을 여기서 커밋해 확정한다.
        await db.commit()
        return AuthIdentity(
            email=user.email,
            roles=tuple(sorted(r for r in roles if r in _PLATFORM_ROLES)),
            source="session-cookie",
        )


async def actor_from_request(request: Request) -> str:
    """감사 로그 actor 용 — ``dp_session`` 쿠키로 로그인 사용자 이메일을 best-effort
    로 해석한다. 쿠키가 없거나 세션이 만료됐거나 해석에 실패하면 ``"anonymous"``.

    인증 게이트가 아니라 신원 *라벨링* 용도이므로 **절대 예외를 던지지 않는다** —
    신원 해석 실패가 감사 기록 자체를 막아선 안 되기 때문이다. 회원가입 사용자는
    email=아이디라 이 값이 곧 로그인 아이디가 된다(시드 사용자는 실제 이메일).
    """
    try:
        ident = await _identity_from_session_cookie(
            request, request.cookies.get(SESSION_COOKIE)
        )
        return ident.email if ident is not None else "anonymous"
    except Exception:  # noqa: BLE001 — best-effort 라벨링: 요청을 절대 깨지 않는다
        return "anonymous"


async def get_current_identity(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
    dp_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> AuthIdentity:
    """이 요청의 활성 신원을 해석한다.

    해석 순서(위에서부터 먼저 성공하는 경로를 채택):

    1. ``dp_session`` 쿠키 → 서버측 세션 행. 사용자가 로그인/검증을 마친 뒤
       SPA의 주 경로다. 쿠키가 유효하면 여기서 바로 반환한다.
    2. Bearer 토큰이 있으면 → strict가 아니어도 반드시 검증한다. 잘못된 토큰을
       조용히 데모 신원으로 강등(downgrade)하지 않는다(SECURITY-09) — 그랬다간
       검증 실패가 우회 가능한 허점이 되기 때문이다.
    3. 토큰 없음 + strict → 401.
    4. 토큰 없음 + 비-strict → 데모 폴백(``X-User-Email`` 헤더나 시드된 admin).
       기존 초기 구동 흐름이 계속 동작하게 한다.

    쿠키를 토큰보다 우선하는 이유: 로그인한 SPA의 일반 요청에는 토큰이 없고
    쿠키만 자동으로 실리므로, 가장 흔한 경로를 가장 먼저 처리해 불필요한 토큰
    검증을 건너뛴다.
    """
    cookie_identity = await _identity_from_session_cookie(request, dp_session)
    if cookie_identity is not None:
        return cookie_identity

    verifier: OidcVerifier | None = getattr(request.app.state, "oidc_verifier", None)
    strict: bool = bool(getattr(request.app.state, "oidc_strict", False))
    has_bearer = bool(authorization and authorization.lower().startswith("bearer "))

    if has_bearer and verifier is not None:
        token = authorization.split(" ", 1)[1].strip()
        try:
            claims = verifier.verify(token)
        except jwt.PyJWTError:
            # 검증 실패의 구체적 사유는 숨기고 일반화된 401만 반환(SECURITY-09).
            # ``from None``으로 원본 예외 체인을 끊어 스택에도 사유가 남지 않게 한다.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid token",
                headers={"WWW-Authenticate": 'Bearer realm="dataplatform"'},
            ) from None
        # 이메일은 신원의 1차 키이므로 반드시 있어야 한다. email이 없으면
        # preferred_username으로 폴백하되, "@"가 없는 값은 이메일로 인정하지 않는다.
        email = claims.get("email") or claims.get("preferred_username")
        if not isinstance(email, str) or "@" not in email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token missing email claim",
            )
        return AuthIdentity(email=email, roles=_roles_from_claims(claims), source="oidc")

    # 토큰이 전혀 없는 경우. strict면 익명을 허용하지 않고 401.
    if strict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": 'Bearer realm="dataplatform"'},
        )
    return _demo_identity(x_user_email)


# 엔드포인트에서 ``ident: CurrentIdentity``로 받기만 하면 위 해석이 자동 주입된다.
CurrentIdentity = Annotated[AuthIdentity, Depends(get_current_identity)]
