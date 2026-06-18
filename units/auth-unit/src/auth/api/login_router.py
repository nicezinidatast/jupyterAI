"""로컬 인증 엔드포인트(signup / login / logout / me / check).

자유 가입: 사용자가 아이디 + 비밀번호를 정하면 이메일 검증 없이 즉시 활성화된다.
이 엔드포인트들은 공유 쿠키-세션 계약을 구현한다:

* 서버가 httpOnly 쿠키 ``dp_session``(값 = 불투명 세션 id)을 설정한다.
* 쿠키 속성은 ``SameSite=Lax; Path=/; HttpOnly``이며, Secure(HTTPS 전용) 여부는
  ``BACKEND_COOKIE_SECURE`` 설정으로 켜고 끈다 — 로컬 HTTP 개발에서 막히지 않게
  하면서 운영에서는 HTTPS로 강제하기 위함이다.
* 브라우저가 동일 출처의 ``/api``·``/jupyter`` 요청에 쿠키를 자동으로 실으므로,
  SPA는 Authorization 헤더를 붙이지 않는다.

식별자는 사용자명(3~20자)이며 ``User.email`` 컬럼에 저장한다 — 이 컬럼은 그저
유일한 문자열 키일 뿐이고(admin 계정도 여기에 문자 그대로 ``"admin"``을 넣는다),
스키마 변경 없이 이메일이든 아이디든 같은 자리에 담기 위한 재사용이다. 갓 생성된
사용자의 기본 역할은 ``Analyst``다. admin 계정은 별도로 부트스트랩된다
(``backend.seed.bootstrap_admin`` 참고).
"""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.api.oidc_dependency import SESSION_COOKIE
from auth.models import User, UserRole
from auth.services.password import hash_password, verify_password
from auth.services.session_service import (
    SESSION_TTL,
    invalidate_session,
    issue_session,
    resolve_session,
)
from backend.db import get_session
from dataplatform_shared.telemetry import get_logger

logger = get_logger("auth.login")

router = APIRouter()
Session = Annotated[AsyncSession, Depends(get_session)]

DEFAULT_ROLE = "Analyst"
# 사용자명: 3~20자, 영문/숫자와 안전한 구분자(_.-) 몇 가지만 허용. 경로·SQL에
# 섞여도 위험하지 않은 문자로 제한해 입력 표면을 좁힌다.
USERNAME_PATTERN = r"^[A-Za-z0-9_.-]{3,20}$"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class SignupBody(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=USERNAME_PATTERN)
    # 최소 4자, 최대 72바이트. 상한 72는 bcrypt가 72바이트 이후를 무시하는 한계에
    # 맞춘 것으로, 잘려서 의도와 다른 해시가 되는 혼동을 입력 단계에서 막는다.
    password: str = Field(min_length=4, max_length=72)


class LoginBody(BaseModel):
    # 로그인은 가입보다 검증을 느슨히 둔다 — 규칙이 바뀌어도 기존 계정으로 계속
    # 로그인되도록(저장된 식별자가 현재 패턴을 벗어나도 인증은 가능하게) 하기 위함.
    username: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    # user_id(UUID 문자열): SPA가 사용자별 JupyterHub 서버 경로(/jupyter/user/<id>)를
    # 만들고, 허브 인증자가 허브 사용자명으로 쓰는 값이라 반드시 내려준다.
    user_id: str
    email: str  # 실제로는 사용자명을 담는다(클라이언트 호환을 위해 필드명은 ``email`` 유지)
    display_name: str | None
    roles: list[str]
    # True면 SPA가 첫 로그인 후 "초기 비밀번호를 변경하세요" 팝업을 띄운다.
    must_change_password: bool = False


class ChangePasswordBody(BaseModel):
    # 본인 비밀번호 변경 요청. 현재 비밀번호는 "비어 있지만 않으면" 통과시켜(min 1),
    # 실제 검증은 저장된 해시 대조로 한다. 새 비밀번호 제약(min 4 / max 72)은 signup과
    # 동일하게 맞춰, 어느 경로로 정하든 같은 규칙이 적용되게 한다.
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=4, max_length=72)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalize_username(username: str) -> str:
    # 가입·로그인에서 동일하게 정규화해, 대소문자나 앞뒤 공백만 다른 입력이
    # 서로 다른 계정처럼 취급되거나 로그인에 실패하지 않게 한다.
    return username.strip().lower()


async def _roles_for(db: AsyncSession, user: User) -> list[str]:
    rows = (
        await db.execute(select(UserRole).where(UserRole.user_id == user.user_id))
    ).scalars()
    return sorted(r.role for r in rows)


def _cookie_secure(request: Request) -> bool:
    settings = getattr(request.app.state, "settings", None)
    return bool(getattr(settings, "cookie_secure", False))


def _set_session_cookie(response: Response, request: Request, session_id) -> None:
    # 쿠키 속성은 모듈 도크스트링의 계약과 일치해야 한다. httponly로 JS 접근을
    # 막고, samesite=lax로 교차 사이트 요청에 쿠키가 따라가는 범위를 제한해
    # CSRF(요청 위조) 표면을 줄인다. max_age는 세션 TTL과 동일하게 맞춰 브라우저
    # 측 만료와 서버 측 만료가 어긋나지 않게 한다.
    response.set_cookie(
        key=SESSION_COOKIE,
        value=str(session_id),
        max_age=int(SESSION_TTL.total_seconds()),
        path="/",
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(request),
    )


def _user_payload(user: User, roles: list[str]) -> dict[str, object]:
    return {
        "user": UserOut(
            user_id=str(user.user_id),
            email=user.email,
            display_name=user.display_name,
            roles=sorted(roles),
            must_change_password=user.must_change_password,
        ).model_dump()
    }


def _session_token(request: Request) -> str | None:
    """요청에서 세션 토큰을 꺼낸다 — ``dp_session`` 쿠키 우선, 없으면
    ``Authorization: Bearer <session_id>`` 헤더를 허용한다.

    Bearer를 허용하는 이유: JupyterHub의 PlatformAuthenticator가 브라우저 쿠키 없이
    서버-서버로 ``Authorization: Bearer <token>``을 붙여 ``/api/auth/me``를 호출해
    사용자를 검증하기 때문이다. 토큰 값은 세션 id 그대로이며, 동일 신뢰 도메인(포털과
    같은 오리진·내부망) 안에서만 오간다.
    """
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        return cookie
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip() or None
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/signup")
async def signup(
    body: SignupBody, db: Session, request: Request, response: Response
) -> dict[str, object]:
    """새 계정을 등록(즉시 활성)하고 세션을 시작한다.

    사용자명이 이미 있으면 409. 새 사용자는 기본 역할 ``Analyst``를 갖고 곧바로
    로그인된다(``dp_session`` 쿠키 설정). 사용자 생성·역할 부여·세션 발급을 한
    트랜잭션으로 묶어 한 번에 commit하므로, 중간에 실패하면 전부 롤백된다.
    """
    username = _normalize_username(body.username)
    existing = (
        await db.execute(select(User).where(User.email == username))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="exists")

    user = User(
        user_id=uuid4(),
        email=username,
        display_name=username,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    db.add(UserRole(user_id=user.user_id, role=DEFAULT_ROLE))
    session_id = await issue_session(db, user.user_id)
    await db.commit()

    _set_session_cookie(response, request, session_id)
    logger.info("auth_signup", username=username)
    return _user_payload(user, [DEFAULT_ROLE])


@router.post("/login")
async def login(
    body: LoginBody, db: Session, request: Request, response: Response
) -> dict[str, object]:
    """비밀번호 로그인. 성공 시 ``dp_session``을 설정한다.

    401 ``invalid_credentials`` — 없는 아이디이거나 비밀번호 불일치.
    """
    username = _normalize_username(body.username)
    user = (
        await db.execute(select(User).where(User.email == username))
    ).scalar_one_or_none()

    # 사용자 없음·비활성·비밀번호 불일치를 하나의 동일한 401로 묶는다 — 어느
    # 경우인지 구분해 응답하면 공격자가 "존재하는 아이디"를 가려낼 수 있으므로
    # (계정 열거, account enumeration) 의도적으로 같은 메시지를 준다.
    if (
        user is None
        or not user.is_active
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="invalid_credentials")

    session_id = await issue_session(db, user.user_id)
    await db.commit()

    _set_session_cookie(response, request, session_id)
    roles = await _roles_for(db, user)
    logger.info("auth_login", username=username)
    return _user_payload(user, roles)


@router.post("/logout")
async def logout(
    db: Session,
    request: Request,
    response: Response,
) -> dict[str, bool]:
    """현재 세션 행을 폐기하고 쿠키를 지운다.

    서버측 폐기와 브라우저측 쿠키 삭제를 모두 수행한다 — 서버에서 행을 무효화해야
    탈취된 쿠키가 더는 통하지 않고, 쿠키 삭제는 같은 브라우저의 재전송을 막는다.
    쿠키가 없거나 이미 폐기됐어도 항상 성공 응답을 준다(멱등).
    """
    cookie_value = request.cookies.get(SESSION_COOKIE)
    await invalidate_session(db, cookie_value)
    await db.commit()
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
async def me(db: Session, request: Request) -> dict[str, object]:
    """활성 사용자의 프로필을 반환하고, 쿠키가 해석되지 않으면 401.

    SPA가 새로고침 후 현재 로그인 상태와 역할을 다시 채우는 데 쓰는 엔드포인트다.
    JupyterHub 인증자도 Bearer 토큰으로 이 엔드포인트를 호출해 사용자를 확인한다.
    """
    cookie_value = _session_token(request)
    resolved = await resolve_session(db, cookie_value)
    if resolved is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    user, roles = resolved
    await db.commit()  # resolve_session이 갱신한 last_seen_at을 확정
    return _user_payload(user, roles)


@router.get("/check")
async def check(db: Session, request: Request) -> dict[str, object]:
    """가벼운 인증 확인 프로브: 인증되면 200 ``{}``, 아니면 401.

    프로필 본문이 필요 없는 곳(예: 라우팅 가드)에서 인증 여부만 빠르게 확인하기
    위한 용도라 ``/me``보다 응답을 최소화한다.
    """
    cookie_value = _session_token(request)
    resolved = await resolve_session(db, cookie_value)
    if resolved is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    await db.commit()
    return {}


@router.get("/jupyter-token")
async def jupyter_token(db: Session, request: Request) -> dict[str, str]:
    """로그인된 사용자가 JupyterHub에 로그인할 때 쓸 단기 토큰을 돌려준다.

    SPA는 이 값을 JupyterHub 로그인의 ``platform_token``으로 넘기고, 허브의
    PlatformAuthenticator는 그 토큰을 Bearer로 ``/api/auth/me``에 검증해 사용자를
    확정한다(쿠키→사용자별 주피터 서버로 이어지는 다리).

    현재 토큰은 세션 id를 그대로 쓴다. ``dp_session``은 httpOnly라 JS가 직접 읽지
    못하므로, 같은 세션을 식별하는 이 값을 본문으로 한 번 내려 주는 것이다. 동일
    오리진(포털)·내부망 안에서만 쓰이며, 세션이 폐기되면 이 토큰도 즉시 무효가 된다.
    """
    token = _session_token(request)
    resolved = await resolve_session(db, token)
    if resolved is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    await db.commit()
    assert token is not None  # resolve_session이 통과했으므로 토큰은 존재한다
    return {"token": token}


@router.post("/change-password")
async def change_password(
    body: ChangePasswordBody, db: Session, request: Request
) -> dict[str, bool]:
    """로그인한 사용자가 자기 비밀번호를 바꾼다.

    현재 세션 쿠키로 본인을 식별한 뒤, **반드시 현재 비밀번호를 확인하고 나서야**
    새 비밀번호로 교체한다. 쿠키만 탈취한 공격자가 곧바로 비밀번호를 바꿔 계정을
    영구 장악하지 못하게 막는 방어이며(쿠키 폐기와 별개의 2차 관문), 본인 확인이
    끝났으므로 현재 세션은 그대로 유지한다(재로그인 강제하지 않음).

    오류 응답:
    * 401 ``unauthenticated`` — 세션이 없거나 만료/폐기됨.
    * 400 ``no_local_password`` — OIDC 전용 사용자라 바꿀 로컬 비밀번호 자체가 없음.
    * 400 ``invalid_current_password`` — 현재 비밀번호 불일치.
    """
    cookie_value = request.cookies.get(SESSION_COOKIE)
    resolved = await resolve_session(db, cookie_value)
    if resolved is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    user, _roles = resolved

    # OIDC/Keycloak로만 인증하는 사용자는 로컬 해시가 없어 변경 대상이 없다.
    if not user.password_hash:
        raise HTTPException(status_code=400, detail="no_local_password")
    # 현재 비밀번호를 직접 대조한다. resolve_session이 돌려준 user는 이미 이 db
    # 세션에 붙어 있으므로, 해시를 갱신하고 commit하면 그대로 영속된다.
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="invalid_current_password")

    user.password_hash = hash_password(body.new_password)
    # 본인이 직접 바꿨으니 초기 비밀번호 변경 안내 플래그를 해제한다(팝업 재노출 방지).
    user.must_change_password = False
    await db.commit()
    logger.info("auth_password_changed", username=user.email)
    return {"ok": True}
