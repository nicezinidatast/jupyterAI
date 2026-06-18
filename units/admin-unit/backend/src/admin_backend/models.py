"""백업·복원 리허설·분기별 접근권한 검토 이력을 저장하는 ORM 모델.

admin-unit이 직접 소유하는 테이블만 여기에 정의한다.
다른 단위(auth, data 등)의 테이블은 각 단위의 models.py에 있으며,
router.py가 어드민 권한으로 교차 접근한다(설계 근거: components.md §11.1).

DB 방언(dialect) 중립성:
- UUID 칼럼: PostgreSQL은 네이티브 UUID 타입, SQLite는 CHAR(32)로 폴백.
- JSONB 칼럼: PostgreSQL에서는 JSONB(인덱스 지원), SQLite 테스트 환경에서는 JSON으로 폴백.
  ``JSONB().with_variant(JSON(), "sqlite")`` 패턴이 이 두 동작을 하나의 매핑으로 통합한다.
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
    """백업 실행 이력 한 건.

    state 칼럼은 DB 레벨 CheckConstraint로 'running'·'success'·'failed' 세 값만
    허용한다. 애플리케이션 계층과 DB 계층에서 이중으로 상태를 제한하므로,
    ORM을 우회한 직접 SQL 수정도 잘못된 값을 막을 수 있다.

    BackupService는 "running" 행을 먼저 커밋하고 pg_dump가 끝난 뒤 별도
    트랜잭션으로 최종 상태를 업데이트한다. 따라서 프로세스가 중간에 죽어도
    "running" 상태의 고아 행이 남아 운영자가 인지할 수 있다.
    """

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
    # 'running' → 'success' | 'failed' 단방향 전이만 허용 (CheckConstraint 참조).
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    # 덤프 파일의 절대 경로 또는 오브젝트 스토리지 URI.
    location: Mapped[str | None] = mapped_column(String(1024))
    # 실패 시 stderr 또는 예외 메시지를 저장한다. 성공이면 NULL.
    error: Mapped[str | None] = mapped_column(Text)


class RestoreRehearsal(Base):
    """복원 리허설(비파괴적 검증) 실행 이력 한 건.

    프로덕션 DB를 건드리지 않고 특정 백업 파일을 격리 환경에서 복원해 무결성을
    검증하는 용도. backup_id 외래키로 어느 백업을 대상으로 한 리허설인지 추적한다.

    report 칼럼(JSONB)에는 복원 소요 시간·레코드 수·체크섬 비교 등의 구조화된
    결과물을 자유 형식으로 저장한다. 스키마를 강제하지 않는 이유는 검증 절차가
    대상 DB 종류에 따라 달라지기 때문이다.
    """

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
    # 복원 검증 결과 상세 리포트. JSONB(PostgreSQL) / JSON(SQLite) 방언 자동 전환.
    report: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite")
    )


class QuarterlyAccessReview(Base):
    """분기별 접근권한 정기 검토 이력.

    개인정보보호 규정 및 사내 보안 정책에 따라 분기마다 사용자·역할 접근권한을
    검토하고, 결과 리포트 경로를 여기에 기록한다.

    quarter 칼럼은 UNIQUE 제약이 있어 동일 분기 이중 생성을 DB 레벨에서 막는다.
    형식 예시: "2026Q2". report_path는 로컬 파일 경로 또는 오브젝트 스토리지 URI.
    """

    __tablename__ = "quarterly_access_reviews"

    review_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    # UNIQUE 제약 — 동일 분기에 중복 생성 방지. 예: "2026Q2".
    quarter: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    report_path: Mapped[str] = mapped_column(String(1024), nullable=False)
