"""Backup, restore-rehearsal, quarterly access review tracking."""

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
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Backup(Base):
    __tablename__ = "backups"
    __table_args__ = (
        CheckConstraint("state IN ('running','success','failed')", name="ck_backup_state"),
    )

    backup_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    target: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    location: Mapped[str | None] = mapped_column(String(1024))
    error: Mapped[str | None] = mapped_column(Text)


class RestoreRehearsal(Base):
    __tablename__ = "restore_rehearsals"
    __table_args__ = (
        CheckConstraint("state IN ('running','success','failed')", name="ck_rehearsal_state"),
    )

    rehearsal_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    backup_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("backups.backup_id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    report: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite")
    )


class QuarterlyAccessReview(Base):
    __tablename__ = "quarterly_access_reviews"

    review_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    quarter: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    report_path: Mapped[str] = mapped_column(String(1024), nullable=False)
