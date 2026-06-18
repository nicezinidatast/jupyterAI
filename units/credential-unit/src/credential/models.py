"""Credential 메타데이터 모델.

평문 시크릿은 Vault(또는 LocalKmsAdapter)에 보관하며 이 DB에는 절대 저장하지 않는다.
DB에는 경로(vault_path), 스코프, 소유자 등 메타데이터만 존재한다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SecretsStorage(Base):
    """Fernet 암호문(at-rest ciphertext)을 저장하는 테이블 — LocalKmsAdapter 전용.

    Credential.vault_path를 기본 키로 사용해 어댑터 계층과 동일한 경로 네임스페이스를 공유한다.
    암호화 키(``BACKEND_CREDENTIAL_KEY``)는 백엔드 프로세스만 보유하며
    DB 행은 불투명한 암호문만 포함한다 — 평문은 절대 기록되지 않는다.
    """

    __tablename__ = "secrets_storage"

    path: Mapped[str] = mapped_column(String(512), primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # rotated_at: LocalKmsAdapter.write()가 기존 행을 갱신할 때 채운다.
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Credential(Base):
    """자격증명 메타데이터 행.

    DB 레벨 제약:
      - ck_cred_scope: scope는 'shared' 또는 'personal' 만 허용한다.
      - ck_scope_owner_consistent: shared이면 owner_user_id가 NULL이어야 하고,
        personal이면 owner_user_id가 NOT NULL이어야 한다.
      - uq_cred_name: (scope, owner_user_id, name) 복합 유니크 — 같은 소유자가
        같은 이름의 Credential을 중복 등록하지 못하도록 막는다.

    soft delete 방식: deleted_at이 NULL이 아니면 논리적으로 삭제된 상태다.
    물리 행은 보존되므로 감사 이력 추적이 가능하다.
    """

    __tablename__ = "credentials"
    __table_args__ = (
        CheckConstraint("scope IN ('shared', 'personal')", name="ck_cred_scope"),
        CheckConstraint(
            "(scope = 'shared' AND owner_user_id IS NULL) OR "
            "(scope = 'personal' AND owner_user_id IS NOT NULL)",
            name="ck_scope_owner_consistent",
        ),
        UniqueConstraint("scope", "owner_user_id", "name", name="uq_cred_name"),
    )

    credential_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    owner_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # vault_path: Vault(또는 SecretsStorage)에서 이 Credential의 시크릿 위치를 나타낸다.
    vault_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # deleted_at: NULL이면 활성, NOT NULL이면 소프트 삭제 상태.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
