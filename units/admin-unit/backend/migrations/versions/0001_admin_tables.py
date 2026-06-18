"""admin-unit 초기 스키마 마이그레이션.

이 마이그레이션이 생성하는 테이블:
- backups: pg_dump / SQLite 백업 실행 이력.
- restore_rehearsals: 백업 파일 무결성 검증(복원 리허설) 이력.
- quarterly_access_reviews: 분기별 접근권한 정기 검토 리포트 경로 이력.

이 세 테이블은 admin-unit이 직접 소유하며, 다른 유닛 테이블을
참조하거나 참조받지 않는다(분리된 경계).

Revision ID: 0001_admin_initial
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_admin_initial"
down_revision = None  # 이 마이그레이션이 admin-unit 브랜치의 최초 리비전이다.
branch_labels = None
depends_on = None

# 방언 중립적 타입 별칭.
# PostgreSQL 환경에서는 네이티브 UUID/JSONB를 사용하고,
# SQLite 테스트 환경에서는 Alembic이 자동으로 호환 타입으로 처리한다.
_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSON = sa.dialects.postgresql.JSONB


def upgrade() -> None:
    """세 테이블을 생성한다.

    state 칼럼에 CheckConstraint를 붙이는 이유:
    ORM 계층을 우회한 직접 SQL 조작에서도 잘못된 상태 값이 삽입되는 것을
    DB 레벨에서 막기 위해서다.
    """
    op.create_table(
        "backups",
        sa.Column("backup_id", _UUID, primary_key=True),
        sa.Column("target", sa.String(64), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        # 허용 상태: 'running' → 'success' | 'failed' (CheckConstraint로 강제).
        sa.Column("state", sa.String(16), nullable=False, server_default="running"),
        sa.Column("size_bytes", sa.BigInteger),
        sa.Column("location", sa.String(1024)),
        sa.Column("error", sa.Text),
        sa.CheckConstraint("state IN ('running','success','failed')", name="ck_backup_state"),
    )
    op.create_table(
        "restore_rehearsals",
        sa.Column("rehearsal_id", _UUID, primary_key=True),
        sa.Column(
            "backup_id",
            _UUID,
            # backups를 참조하는 외래키 — 대상 백업 추적용.
            sa.ForeignKey("backups.backup_id"),
            nullable=False,
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("state", sa.String(16), nullable=False, server_default="running"),
        # 복원 검증 상세 결과를 자유 형식 JSON으로 저장한다.
        sa.Column("report", _JSON),
        sa.CheckConstraint(
            "state IN ('running','success','failed')", name="ck_rehearsal_state"
        ),
    )
    op.create_table(
        "quarterly_access_reviews",
        sa.Column("review_id", _UUID, primary_key=True),
        # UNIQUE: 동일 분기에 중복 생성 방지. 형식 예: "2026Q2".
        sa.Column("quarter", sa.String(8), nullable=False, unique=True),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("report_path", sa.String(1024), nullable=False),
    )


def downgrade() -> None:
    """외래키 의존 순서의 역순으로 테이블을 삭제한다.

    quarterly_access_reviews와 restore_rehearsals를 먼저 삭제하고
    마지막에 backups를 삭제해야 외래키 제약 위반이 생기지 않는다.
    """
    for table in ("quarterly_access_reviews", "restore_rehearsals", "backups"):
        op.drop_table(table)
