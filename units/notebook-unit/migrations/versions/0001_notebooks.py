"""notebook-unit schema.

Revision ID: 0001_notebook_initial
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_notebook_initial"
down_revision = None
branch_labels = None
depends_on = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSON = sa.dialects.postgresql.JSONB


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("workspace_id", _UUID, primary_key=True),
        sa.Column("owner_user_id", _UUID, nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("git_repo_url", sa.String(512), nullable=False),
        sa.Column("git_branch", sa.String(64), nullable=False, server_default="main"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("kind IN ('personal','team')", name="ck_ws_kind"),
    )
    op.create_table(
        "notebooks",
        sa.Column("notebook_id", _UUID, primary_key=True),
        sa.Column(
            "workspace_id",
            _UUID,
            sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("created_by", _UUID, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "notebook_versions",
        sa.Column("version_id", _UUID, primary_key=True),
        sa.Column(
            "notebook_id",
            _UUID,
            sa.ForeignKey("notebooks.notebook_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("content", _JSON, nullable=False),
        sa.Column(
            "saved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("saved_by", _UUID, nullable=False),
        sa.Column("is_autosave", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("git_commit_sha", sa.String(64)),
    )
    op.create_table(
        "git_commit_outbox",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "notebook_version_id",
            _UUID,
            sa.ForeignKey("notebook_versions.version_id"),
            nullable=False,
        ),
        sa.Column("commit_message", sa.String(512)),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("state", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("last_error", sa.Text),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("state IN ('queued','committed','failed')", name="ck_git_outbox_state"),
    )
    op.create_table(
        "share_links",
        sa.Column("link_id", _UUID, primary_key=True),
        sa.Column(
            "notebook_id",
            _UUID,
            sa.ForeignKey("notebooks.notebook_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("permission", sa.String(16), nullable=False),
        sa.Column("created_by", _UUID, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("permission IN ('read','execute','edit')", name="ck_share_perm"),
    )
    op.create_table(
        "share_audience",
        sa.Column(
            "link_id",
            _UUID,
            sa.ForeignKey("share_links.link_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("subject_user_id", _UUID, primary_key=True),
        sa.Column("subject_role", sa.String(32), primary_key=True),
        sa.CheckConstraint(
            "(subject_user_id IS NULL) <> (subject_role IS NULL)",
            name="ck_audience_subject_xor",
        ),
    )


def downgrade() -> None:
    for table in (
        "share_audience",
        "share_links",
        "git_commit_outbox",
        "notebook_versions",
        "notebooks",
        "workspaces",
    ):
        op.drop_table(table)
