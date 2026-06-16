"""admin-unit schema.

Revision ID: 0001_admin_initial
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_admin_initial"
down_revision = None
branch_labels = None
depends_on = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSON = sa.dialects.postgresql.JSONB


def upgrade() -> None:
    op.create_table(
        "backups",
        sa.Column("backup_id", _UUID, primary_key=True),
        sa.Column("target", sa.String(64), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
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
            sa.ForeignKey("backups.backup_id"),
            nullable=False,
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("state", sa.String(16), nullable=False, server_default="running"),
        sa.Column("report", _JSON),
        sa.CheckConstraint(
            "state IN ('running','success','failed')", name="ck_rehearsal_state"
        ),
    )
    op.create_table(
        "quarterly_access_reviews",
        sa.Column("review_id", _UUID, primary_key=True),
        sa.Column("quarter", sa.String(8), nullable=False, unique=True),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("report_path", sa.String(1024), nullable=False),
    )


def downgrade() -> None:
    for table in ("quarterly_access_reviews", "restore_rehearsals", "backups"):
        op.drop_table(table)
