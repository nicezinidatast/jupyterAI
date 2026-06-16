"""Initial auth schema.

Revision ID: 0001_auth_initial
Create Date: 2026-05-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_auth_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(32), primary_key=True),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("assigned_by", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.CheckConstraint(
            "role IN ('Admin','Analyst','Viewer','Auditor')", name="ck_role_enum"
        ),
    )
    op.create_index("idx_user_roles_role", "user_roles", ["role"])

    op.create_table(
        "sessions",
        sa.Column("session_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id"),
            nullable=False,
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "idx_sessions_user_active",
        "sessions",
        ["user_id"],
        postgresql_where=sa.text("invalidated_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_sessions_user_active", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("idx_user_roles_role", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_table("users")
