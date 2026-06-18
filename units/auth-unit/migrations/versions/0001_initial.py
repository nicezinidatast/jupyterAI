"""초기 auth 스키마.

Alembic 마이그레이션으로 users·user_roles·sessions 세 테이블을 생성한다.
모델(``auth.models``)과 동일한 구조를 DB에 반영하되, 여기서는 인덱스·제약 등
운영에 필요한 물리 설계까지 포함한다.

Revision ID: 0001_auth_initial
Create Date: 2026-05-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# Alembic가 마이그레이션 순서를 잇는 메타데이터. 최초 리비전이라 down_revision은 None.
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
        # DB 차원에서 역할 집합을 강제한다 — 애플리케이션을 우회한 직접 INSERT도 막는다.
        sa.CheckConstraint(
            "role IN ('Admin','Analyst','Viewer','Auditor')", name="ck_role_enum"
        ),
    )
    # 역할별 사용자 조회(예: 활성 Admin 카운트)를 빠르게 하기 위한 인덱스.
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
    # 사용자별 "활성" 세션만 인덱싱하는 부분 인덱스(partial index). 폐기된 행은
    # 인덱스에서 빠져 크기와 조회 비용을 줄인다 — 보통 활성 세션만 찾기 때문이다.
    op.create_index(
        "idx_sessions_user_active",
        "sessions",
        ["user_id"],
        postgresql_where=sa.text("invalidated_at IS NULL"),
    )


def downgrade() -> None:
    # upgrade의 역순으로 되돌린다 — 외래키 의존성 때문에 자식 테이블부터 지운다.
    op.drop_index("idx_sessions_user_active", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("idx_user_roles_role", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_table("users")
