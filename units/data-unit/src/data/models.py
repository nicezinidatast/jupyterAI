"""연결·권한(grant)·PII 정책·쿼리 실행 이력에 대한 SQLAlchemy 모델.

JSONB 컬럼은 ``.with_variant(JSON(), "sqlite")``로 sqlite 폴백을 둔다 —
테스트는 인메모리 sqlite로 돌고 운영은 Postgres라, 양쪽에서 같은 모델이
동작하게 하기 위함이다. UUID 기본키와 CHECK 제약으로 도메인 불변식을
데이터베이스 수준에서 강제한다(애플리케이션 버그가 있어도 잘못된 값이
저장되지 못하게 막는 마지막 방어선).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
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
    # 등록된 데이터 소스(외부 DB) 한 건. 자격증명 자체는 여기 두지 않고
    # credential_id로 참조만 한다(비밀은 별도 보관소에 암호화 저장).
    __tablename__ = "connections"
    __table_args__ = (
        # engine 값을 허용 목록으로 제한해, 정의되지 않은 엔진 문자열이 저장돼
        # 팩토리 분기에서 예기치 않게 새는 일을 DB 수준에서 막는다.
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
        JSONB().with_variant(JSON(), "sqlite"), server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ConnectionGrant(Base):
    # 연결에 대한 접근 제어 목록(ACL)의 권위 테이블. 한 grant는 "특정 사용자"
    # 또는 "특정 역할" 중 정확히 하나에만 권한을 부여한다.
    __tablename__ = "connection_grants"
    __table_args__ = (
        CheckConstraint("action IN ('read','execute','admin')", name="ck_grant_action"),
        # XOR 제약: subject_user_id와 subject_role 중 정확히 하나만 채워져야 한다.
        # 둘 다 비거나 둘 다 채우면 권한 주체가 모호해지므로 DB가 거절한다.
        CheckConstraint(
            "(subject_user_id IS NULL) <> (subject_role IS NULL)",
            name="ck_grant_subject_xor",
        ),
        # 같은 (연결, 주체, action) 조합이 중복 등록되지 않도록 유일성 보장.
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
    # 관리자가 등록하는 PII 탐지 패턴. is_active로 켜고 끌 수 있으며, 활성
    # 패턴만 마스킹·조회 힌트에 반영된다. regex는 저장 전에 validate_regex로
    # ReDoS 안전성을 검증한다(pii_masking.validate_regex 참고).
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
    # 연결·테이블·컬럼 단위의 노출 정책. (connection_id, table_name,
    # column_name)이 복합 기본키라 같은 컬럼에 정책이 중복될 수 없다.
    # mask=가림, allow=원본 노출, block=결과에서 제외.
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
    # 쿼리 실행 이력(감사·디버깅용). 원문 SQL·파라미터 대신 해시만 저장해,
    # 이력 테이블에 민감정보가 평문으로 남지 않게 한다.
    __tablename__ = "query_executions"

    query_handle: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    connection_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sql_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # 원문 대신 SHA-256 등 해시
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
    # 업로드된 파일의 메타데이터. 실제 바이트는 공유 볼륨에 저장되고 여기에는
    # storage_path로 위치만 기록한다(file_ingest.ingest_upload 참고).
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
