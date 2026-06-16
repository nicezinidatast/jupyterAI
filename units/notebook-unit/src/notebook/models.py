"""Notebook + share link + Git outbox SQLAlchemy models."""

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


class GitCommitOutbox(Base):
    __tablename__ = "git_commit_outbox"
    __table_args__ = (
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


class ShareLink(Base):
    __tablename__ = "share_links"
    __table_args__ = (
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


class ShareAudience(Base):
    __tablename__ = "share_audience"
    __table_args__ = (
        CheckConstraint(
            "(subject_user_id IS NULL) <> (subject_role IS NULL)",
            name="ck_audience_subject_xor",
        ),
    )

    # Surrogate PK so the (user_id | role) XOR can use real NULLs — Postgres
    # promotes any PK column to NOT NULL, which collides with our XOR rule.
    audience_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    link_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("share_links.link_id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    subject_role: Mapped[str | None] = mapped_column(String(32))
