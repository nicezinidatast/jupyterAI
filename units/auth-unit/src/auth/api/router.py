"""auth-unit 공개 API.

세션/로그인 엔드포인트는 :mod:`auth.api.login_router`에 있다. 이 모듈은 그것들을
포함한 단일 ``router``를 재노출(re-export)하며, ``backend.main``이 이 하나만
마운트하면 인증 관련 라우트가 모두 붙는다 — 통합 지점을 한 곳으로 모으기 위함이다.

신원은 :func:`auth.api.oidc_dependency.get_current_identity`가 다음 순서로 해석한다:

* **``dp_session`` httpOnly 쿠키** → 서버측 세션 행(로그인/검증 이후 주 경로);
* OIDC Bearer 토큰(Keycloak이 연결된 경우); 그리고
* 데모 폴백(``X-User-Email`` 헤더나 시드된 admin) — 초기 구동용.
"""

from __future__ import annotations

from fastapi import APIRouter

from auth.api.login_router import router as login_router

# 모든 인증 라우트는 ``/api/auth`` 접두사 아래로 모은다.
router = APIRouter(prefix="/api/auth", tags=["auth"])

# signup/login/logout/me/check 마운트.
router.include_router(login_router)
