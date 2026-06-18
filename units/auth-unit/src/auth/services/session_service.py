"""불투명(opaque) 서버측 세션 수명주기.

세션은 ``sessions`` 테이블의 한 행이며, 그 ``session_id``(UUID, 범용 고유
식별자)를 그대로 브라우저의 ``dp_session`` httpOnly(자바스크립트에서 읽을 수
없는) 쿠키 값으로 넘겨준다. 여기에는 JWT(JSON Web Token)도 없고 클라이언트가
해석할 수 있는 정보도 전혀 없다 — 즉 쿠키 자체는 의미 없는 식별자일 뿐이고
실제 상태는 모두 서버 DB에 있다. 이 "불투명" 설계의 이점은 세션 폐기(revocation)가
``UPDATE sessions SET invalidated_at = now()`` 한 줄로 끝난다는 점이다. JWT처럼
만료 전까지 살아 있는 토큰을 따로 블랙리스트로 관리할 필요가 없다.

인증된 요청의 신원 해석 "순서"는 ``auth.api.oidc_dependency``가 책임진다.
이 모듈은 그 순서에 쓰이는 원시 연산(primitive)만 제공한다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import Session as SessionRow
from auth.models import User, UserRole

# 세션 수명 7일(계약상 기본값). TTL은 time-to-live(유효 기간)의 약자.
SESSION_TTL = timedelta(days=7)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def issue_session(db: AsyncSession, user_id: UUID) -> UUID:
    """``user_id``에 대한 새 세션 행을 만들고 그 id(=쿠키 값)를 반환한다.

    행을 ``add``만 하고 commit은 하지 않는다 — 트랜잭션 커밋 책임은 호출자에게
    있다. 로그인·회원가입 핸들러가 사용자 생성·세션 발급을 한 트랜잭션으로 묶어
    원자적으로 처리할 수 있게 하기 위한 의도다.
    """
    now = _now()
    session_id = uuid4()
    db.add(
        SessionRow(
            session_id=session_id,
            user_id=user_id,
            issued_at=now,
            expires_at=now + SESSION_TTL,
            invalidated_at=None,
            last_seen_at=now,
        )
    )
    return session_id


def _coerce_session_id(raw: str | None) -> UUID | None:
    # 쿠키 값은 신뢰할 수 없는 외부 입력이므로 UUID 파싱을 방어적으로 한다.
    # 비거나 형식이 깨진 값은 예외를 던지지 않고 None으로 떨어뜨려, 호출부에서
    # "인증 실패"와 동일하게 다루도록 한다(공격자에게 실패 원인을 흘리지 않음).
    if not raw:
        return None
    try:
        return UUID(raw)
    except (ValueError, AttributeError):
        return None


async def resolve_session(
    db: AsyncSession, cookie_value: str | None
) -> tuple[User, list[str]] | None:
    """``dp_session`` 쿠키 값을 ``(User, roles)``로 해석하거나 ``None``을 반환한다.

    다음 중 하나라도 해당하면 ``None``을 돌려준다: 쿠키가 없거나 형식이 깨짐,
    세션 행이 없음, 폐기됨(invalidated), 만료됨(expired), 사용자가 없거나 비활성.
    이 가드들은 위에서 아래로 순서가 중요하다 — 존재→폐기 여부→만료→사용자
    상태 순으로 좁혀가며, 어느 단계든 실패하면 동일하게 익명 처리한다.

    성공 시 ``last_seen_at``을 갱신한다(최선 노력; 여기서 commit하지 않으므로
    요청 자신의 트랜잭션이 이 변경을 함께 커밋해야 실제로 반영된다).
    """
    session_id = _coerce_session_id(cookie_value)
    if session_id is None:
        return None

    row = await db.get(SessionRow, session_id)
    if row is None or row.invalidated_at is not None:
        return None

    # expires_at은 Postgres에서는 시간대 정보가 있는(tz-aware) 값으로 저장되지만
    # SQLite에서는 시간대 정보가 없는(naive) 값으로 돌아올 수 있다. 비교 전에
    # UTC로 정규화해 두 백엔드 모두에서 만료 판정이 정확하도록 맞춘다(naive와
    # aware를 직접 비교하면 TypeError가 난다).
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= _now():
        return None

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None

    roles = [
        r.role
        for r in (
            await db.execute(select(UserRole).where(UserRole.user_id == user.user_id))
        ).scalars()
    ]

    # 최근 접속 시각 갱신(최선 노력). 여기서 commit하지 않고, 요청 자신의
    # 트랜잭션이 커밋해 준다 — 매 인증마다 별도 쓰기 트랜잭션을 열지 않기 위함.
    row.last_seen_at = _now()
    return user, roles


async def invalidate_session(db: AsyncSession, cookie_value: str | None) -> bool:
    """``cookie_value``에 해당하는 세션을 폐기 표시한다. 행을 찾으면 True.

    이미 폐기된 행은 ``invalidated_at``을 다시 덮어쓰지 않는다 — 최초 폐기 시각을
    보존하기 위함이다(이중 로그아웃이 감사 추적을 어지럽히지 않도록). 호출자가
    트랜잭션을 커밋해야 폐기가 확정된다.
    """
    session_id = _coerce_session_id(cookie_value)
    if session_id is None:
        return False
    row = await db.get(SessionRow, session_id)
    if row is None:
        return False
    if row.invalidated_at is None:
        row.invalidated_at = _now()
    return True
