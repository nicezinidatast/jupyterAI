"""사용자·역할·세션의 SQLAlchemy 모델.

세 테이블이 인증 단위의 핵심 상태를 담는다: ``users``(신원), ``user_roles``
(권한), ``sessions``(서버측 세션 행). UUID 컬럼은 Postgres의 네이티브 UUID
타입을 쓰되, SQLite 테스트에서는 자동으로 문자열로 강등되어 동일 코드로 양쪽을
검증할 수 있다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# 시스템이 인정하는 표준 역할 4종. CheckConstraint와 역할 검증의 단일 출처
# (single source of truth)로 쓰여, 정의되지 않은 역할이 DB에 들어가지 못하게 한다.
VALID_ROLES = ("Admin", "Analyst", "Viewer", "Auditor")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    # 유일 키 역할의 문자열. 로컬 가입에서는 사용자명을, OIDC에서는 이메일을 담는
    # 재사용 컬럼이라 이름과 달리 항상 이메일 형식인 것은 아니다.
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    # Nullable인 이유: OIDC/Keycloak 연동 사용자는 로컬 비밀번호가 없다. 로컬 인증
    # 사용자(가입/검증, admin 부트스트랩)만 bcrypt 해시를 가진다. 따라서 해시가
    # None인 것과 "비밀번호 틀림"은 다른 상황이며, 검증 헬퍼가 둘 다 안전하게 처리한다.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    # CheckConstraint로 DB 차원에서도 역할 집합을 강제한다 — 애플리케이션 검증을
    # 우회한 직접 INSERT도 막기 위한 2차 방어선.
    __table_args__ = (
        CheckConstraint(f"role IN {VALID_ROLES}", name="ck_role_enum"),
    )

    # (user_id, role) 복합 기본키라 한 사용자가 같은 역할을 중복으로 가질 수 없다.
    # ondelete="CASCADE"로 사용자 삭제 시 역할 행도 함께 정리된다(고아 행 방지).
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(32), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # 누가 이 역할을 부여했는지 감사용으로 기록(없을 수 있어 nullable).
    assigned_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))

    user: Mapped[User] = relationship(back_populates="roles")


class Session(Base):
    __tablename__ = "sessions"

    # session_id가 곧 ``dp_session`` 쿠키 값이다. 추측 불가능해야 하므로 UUID를 쓴다.
    session_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # invalidated_at이 NULL이 아니면 폐기된 세션. 행을 지우지 않고 표시만 해
    # 폐기 시각을 감사 추적으로 남긴다(로그아웃·강제 만료 이력).
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 마지막 접속 시각. 인증마다 best-effort로 갱신된다(분석·유휴 판단용).
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
