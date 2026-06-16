"""SQLAlchemy models for connections, grants, PII policies, and queries."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Connection(Base):
    __tablename__ = "connections"
    __table_args__ = (
        CheckConstraint(
            "engine IN ('postgres','mysql','oracle','mssql','hive','impala','presto','trino')",
            name="ck_conn_engine",
        ),
    )

    connection_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    engine: Mapped[str] = mapped_column(String(32), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    database: Mapped[str | None] = mapped_column(String(128))
    credential_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    options: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(Text(), "sqlite"), server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ConnectionGrant(Base):
    __tablename__ = "connection_grants"
    __table_args__ = (
        CheckConstraint("action IN ('read','execute','admin')", name="ck_grant_action"),
        CheckConstraint(
            "(subject_user_id IS NULL) <> (subject_role IS NULL)",
            name="ck_grant_subject_xor",
        ),
        UniqueConstraint(
            "connection_id",
            "subject_user_id",
            "subject_role",
            "action",
            name="uq_grant",
        ),
    )

    grant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    connection_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("connections.connection_id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    subject_role: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    granted_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))


class PiiPattern(Base):
    __tablename__ = "pii_patterns"
    __table_args__ = (
        CheckConstraint("kind IN ('name','rrn','phone','email','custom')", name="ck_pii_kind"),
    )

    pattern_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    regex: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ColumnPolicy(Base):
    __tablename__ = "column_policies"
    __table_args__ = (
        CheckConstraint("policy IN ('mask','allow','block')", name="ck_col_policy"),
    )

    connection_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("connections.connection_id", ondelete="CASCADE"),
        primary_key=True,
    )
    table_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    column_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    policy: Mapped[str] = mapped_column(String(16), nullable=False)


class QueryExecution(Base):
    __tablename__ = "query_executions"

    query_handle: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    connection_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sql_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    params_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rows_returned: Mapped[int | None] = mapped_column(BigInteger)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    result_status: Mapped[str | None] = mapped_column(String(16))
    is_background: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class FileUpload(Base):
    __tablename__ = "file_uploads"

    file_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
