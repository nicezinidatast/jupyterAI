"""감사 로그 초기 스키마 마이그레이션 — WORM 트리거 포함.

Revision ID: 0001_audit_initial

생성 내용:
  - audit_outbox: outbox 패턴용 이벤트 임시 버퍼 테이블.
  - audit_log: 영구 감사 기록 테이블 (WORM: Write Once Read Many).
  - trig_audit_log_no_modify: audit_log의 UPDATE / DELETE / TRUNCATE를 차단하는
    PL/pgSQL 트리거 — NFR-SEC-14 요건 충족.

WORM 트리거가 있어도 애플리케이션 레이어에서는 INSERT 외 시도를 하지 않아야 한다.
트리거는 최후 방어선이지 유일한 통제 수단이 아니다.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_audit_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_outbox",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("event", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
    )
    # partial index — delivered_at IS NULL 조건으로 미전달 행만 인덱싱해 컨슈머 쿼리를 최적화한다.
    op.create_index(
        "idx_audit_outbox_undelivered",
        "audit_outbox",
        ["id"],
        postgresql_where=sa.text("delivered_at IS NULL"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("actor_id", sa.String(128)),
        sa.Column("resource", sa.String(256)),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("corr_id", sa.String(128)),
        sa.Column("payload", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column(
            "written_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "result IN ('success', 'failure')", name="ck_result_enum"
        ),
    )
    # (actor_id, occurred_at) 복합 인덱스 — 특정 행위자의 시간 범위 조회를 가속한다.
    op.create_index(
        "idx_audit_log_actor_time", "audit_log", ["actor_id", "occurred_at"]
    )

    # WORM 강제 트리거 — audit_log에 대한 UPDATE / DELETE / TRUNCATE를 거부한다.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION block_audit_modification() RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trig_audit_log_no_modify
            BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_log
            EXECUTE FUNCTION block_audit_modification();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trig_audit_log_no_modify ON audit_log;")
    op.execute("DROP FUNCTION IF EXISTS block_audit_modification();")
    op.drop_index("idx_audit_log_actor_time", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("idx_audit_outbox_undelivered", table_name="audit_outbox")
    op.drop_table("audit_outbox")
