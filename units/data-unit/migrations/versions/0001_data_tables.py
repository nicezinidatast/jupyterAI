"""data-unit schema.

Revision ID: 0001_data_initial
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_data_initial"
down_revision = None
branch_labels = None
depends_on = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSON = sa.dialects.postgresql.JSONB


def upgrade() -> None:
    op.create_table(
        "connections",
        sa.Column("connection_id", _UUID, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("engine", sa.String(32), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer, nullable=False),
        sa.Column("database", sa.String(128)),
        sa.Column("credential_id", _UUID, nullable=False),
        sa.Column("options", _JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "engine IN ('postgres','mysql','oracle','mssql','hive','impala','presto','trino')",
            name="ck_conn_engine",
        ),
    )
    op.create_table(
        "connection_grants",
        sa.Column("grant_id", _UUID, primary_key=True),
        sa.Column(
            "connection_id",
            _UUID,
            sa.ForeignKey("connections.connection_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject_user_id", _UUID),
        sa.Column("subject_role", sa.String(32)),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("granted_by", _UUID),
        sa.CheckConstraint("action IN ('read','execute','admin')", name="ck_grant_action"),
        sa.CheckConstraint(
            "(subject_user_id IS NULL) <> (subject_role IS NULL)", name="ck_grant_subject_xor"
        ),
    )
    op.create_table(
        "pii_patterns",
        sa.Column("pattern_id", _UUID, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("regex", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.CheckConstraint("kind IN ('name','rrn','phone','email','custom')", name="ck_pii_kind"),
    )
    op.create_table(
        "column_policies",
        sa.Column(
            "connection_id",
            _UUID,
            sa.ForeignKey("connections.connection_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("table_name", sa.String(128), primary_key=True),
        sa.Column("column_name", sa.String(128), primary_key=True),
        sa.Column("policy", sa.String(16), nullable=False),
        sa.CheckConstraint("policy IN ('mask','allow','block')", name="ck_col_policy"),
    )
    op.create_table(
        "query_executions",
        sa.Column("query_handle", _UUID, primary_key=True),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("connection_id", _UUID, nullable=False),
        sa.Column("sql_hash", sa.String(64), nullable=False),
        sa.Column("params_hash", sa.String(64), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("rows_returned", sa.BigInteger),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("result_status", sa.String(16)),
        sa.Column("is_background", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "file_uploads",
        sa.Column("file_id", _UUID, primary_key=True),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("filename", sa.String(256), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("mime", sa.String(128), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    for table in (
        "file_uploads",
        "query_executions",
        "column_policies",
        "pii_patterns",
        "connection_grants",
        "connections",
    ):
        op.drop_table(table)
