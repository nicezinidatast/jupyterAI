"""Credential metadata. Plaintext lives in Vault, never in this DB."""

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
    """At-rest Fernet ciphertext, keyed by Credential.vault_path.

    Acts as a local Vault stand-in: the encryption key
    (``BACKEND_CREDENTIAL_KEY``) is held only by the backend process. The DB
    row contains opaque ciphertext only — never plaintext.
    """

    __tablename__ = "secrets_storage"

    path: Mapped[str] = mapped_column(String(512), primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Credential(Base):
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
    vault_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
