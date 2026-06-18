"""Outbox + 추가 전용(append-only) 감사 로그 SQLAlchemy 모델.

두 테이블의 역할:
  - AuditOutbox: 도메인 유닛이 이벤트를 삽입하는 임시 버퍼 (outbox 패턴).
  - AuditLog: 컨슈머가 이관한 영구 기록 — DB 트리거가 UPDATE/DELETE를 차단한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AuditOutbox(Base):
    """이벤트 임시 저장소 — 모든 도메인 유닛이 도메인 변경과 같은 트랜잭션에 삽입한다.

    delivered_at이 NULL인 행은 아직 audit_log로 이관되지 않은 미전달 이벤트다.
    OutboxConsumer가 이 컬럼을 기준으로 미처리 행을 선택해 이관 후 delivered_at을 채운다.
    """

    __tablename__ = "audit_outbox"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )
    # Postgres에서는 JSONB(인덱싱 지원), SQLite 테스트에서는 JSON(TEXT 기반)으로 폴백된다.
    event: Mapped[dict[str, Any]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # delivered_at: NULL이면 미전달, NOT NULL이면 audit_log로 이관 완료.
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    """영구 감사 기록 — DB 트리거(NFR-SEC-14)로 추가 전용(append-only) 불변식을 강제한다.

    DB 레벨 제약:
      - ck_result_enum: result는 'success' 또는 'failure' 만 허용한다.
      - trig_audit_log_no_modify(트리거): UPDATE / DELETE / TRUNCATE 시 예외를 발생시킨다.

    occurred_at: 이벤트가 실제로 발생한 시각 (애플리케이션이 기록).
    written_at: 이 행이 DB에 삽입된 시각 (서버 기본값) — 두 값의 차이로 처리 지연을 추적한다.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint("result IN ('success', 'failure')", name="ck_result_enum"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(128))
    resource: Mapped[str | None] = mapped_column(String(256))
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    corr_id: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    written_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
