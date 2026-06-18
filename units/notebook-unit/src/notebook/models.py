"""노트북 + 공유 링크 + Git outbox SQLAlchemy 모델.

JSONB는 Postgres 운영용, sqlite 변형(JSON)은 테스트용으로 한 모델이 두 백엔드를
모두 지원한다. UUID도 마찬가지로 Postgres에서는 네이티브 UUID 타입을 쓴다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("kind IN ('personal','team')", name="ck_ws_kind"),
    )

    workspace_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    owner_user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    git_repo_url: Mapped[str] = mapped_column(String(512), nullable=False)
    git_branch: Mapped[str] = mapped_column(String(64), nullable=False, default="main")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Notebook(Base):
    __tablename__ = "notebooks"

    notebook_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# 저장할 때마다 한 행씩 쌓이는 불변(append-only) 버전 이력.
# content_sha256으로 직전 버전과 비교해 동일 내용 저장은 건너뛴다(멱등성).
class NotebookVersion(Base):
    __tablename__ = "notebook_versions"

    version_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    notebook_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("notebooks.notebook_id", ondelete="CASCADE"),
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    saved_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    is_autosave: Mapped[bool] = mapped_column(default=False)
    git_commit_sha: Mapped[str | None] = mapped_column(String(64))


# Git push 발신함(outbox). 노트북 저장 트랜잭션이 이 행을 함께 남기고,
# AutoCommitOrchestrator가 비동기로 집어 실제 push한다. state로 진행 상태를,
# attempts/last_error로 재시도와 마지막 실패 원인을 추적한다.
class GitCommitOutbox(Base):
    __tablename__ = "git_commit_outbox"
    __table_args__ = (
        # 상태 머신 보호: queued → committed/failed 외의 값은 DB가 거부한다.
        CheckConstraint(
            "state IN ('queued','committed','failed')", name="ck_git_outbox_state"
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )
    notebook_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("notebook_versions.version_id"),
        nullable=False,
    )
    commit_message: Mapped[str | None] = mapped_column(String(512))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# 공유 링크. 부여 권한(permission)과 폐기 시각(revoked_at)을 들고,
# 누구에게 열렸는지는 ShareAudience로 분리해 N:1로 연결한다.
class ShareLink(Base):
    __tablename__ = "share_links"
    __table_args__ = (
        # 권한은 세 등급으로 제한 — share_link 서비스의 등급 비교 불변식과 짝.
        CheckConstraint("permission IN ('read','execute','edit')", name="ck_share_perm"),
    )

    link_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    notebook_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("notebooks.notebook_id", ondelete="CASCADE"),
        nullable=False,
    )
    permission: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# 공유 링크의 대상(audience). 한 행은 특정 사용자 또는 특정 역할 중
# "정확히 하나"만 가리킨다(XOR). resolve에서 이 행들과 요청자를 대조한다.
class ShareAudience(Base):
    __tablename__ = "share_audience"
    __table_args__ = (
        # user_id와 role 중 하나만 채워졌음을 DB 레벨에서 강제(<>는 XOR).
        CheckConstraint(
            "(subject_user_id IS NULL) <> (subject_role IS NULL)",
            name="ck_audience_subject_xor",
        ),
    )

    # 대리(surrogate) PK를 둬서 (user_id | role) XOR이 실제 NULL을 쓸 수 있게 한다 —
    # Postgres는 PK 컬럼을 모두 NOT NULL로 만들어 우리의 XOR 규칙과 충돌하므로,
    # user_id/role을 PK로 쓰지 않고 별도 audience_id를 PK로 둔다.
    audience_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    link_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("share_links.link_id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    subject_role: Mapped[str | None] = mapped_column(String(32))
