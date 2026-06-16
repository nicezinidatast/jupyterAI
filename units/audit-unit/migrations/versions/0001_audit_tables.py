"""Initial audit schema with WORM trigger.

Revision ID: 0001_audit_initial
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
    op.create_index(
        "idx_audit_log_actor_time", "audit_log", ["actor_id", "occurred_at"]
    )

    # WORM enforcement — refuse UPDATE / DELETE / TRUNCATE on audit_log.
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
