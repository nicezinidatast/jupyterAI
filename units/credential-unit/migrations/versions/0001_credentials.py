"""Credential 스키마 초기 마이그레이션.

Revision ID: 0001_credentials

credentials 테이블과 partial index를 생성한다.
partial index(idx_credentials_owner)는 삭제되지 않은 행에 대해서만 owner_user_id를 인덱싱해
개인 Credential 목록 조회 성능을 확보한다.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_credentials"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credentials",
        sa.Column("credential_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("owner_user_id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("vault_path", sa.String(512), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("scope IN ('shared','personal')", name="ck_cred_scope"),
        sa.CheckConstraint(
            "(scope = 'shared' AND owner_user_id IS NULL) OR "
            "(scope = 'personal' AND owner_user_id IS NOT NULL)",
            name="ck_scope_owner_consistent",
        ),
        sa.UniqueConstraint("scope", "owner_user_id", "name", name="uq_cred_name"),
    )
    # deleted_at IS NULL 조건의 partial index — 활성 행만 인덱싱해 인덱스 크기를 최소화한다.
    op.create_index(
        "idx_credentials_owner",
        "credentials",
        ["owner_user_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_credentials_owner", table_name="credentials")
    op.drop_table("credentials")
