"""Local-KMS Vault adapter — Fernet encryption with DB-backed persistence.

This is the production-shaped path for closed networks without HashiCorp Vault.
The Fernet key lives only in the backend process (env var
``BACKEND_CREDENTIAL_KEY``); the DB stores opaque ciphertext keyed by the
Credential ``vault_path``.

The adapter conforms to :class:`credential.adapters.vault.VaultAdapter` and is
a drop-in replacement for ``HvacVaultAdapter``.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import delete, func

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret

from credential.models import SecretsStorage


class LocalKmsAdapter:
    """Fernet-encrypted DB-backed Vault stand-in."""

    def __init__(self, *, key: bytes, session_factory) -> None:
        # Fernet validates key shape on instantiation: 32 url-safe base64 bytes.
        self._fernet = Fernet(key)
        self._session_factory = session_factory

    async def read(self, path: str) -> Result[Secret, DomainError]:
        async with self._session_factory() as session:
            row = await session.get(SecretsStorage, path)
            if row is None:
                return Err(DomainError.NOT_FOUND)
            try:
                plaintext = self._fernet.decrypt(row.ciphertext).decode("utf-8")
            except InvalidToken:
                return Err(DomainError.EXTERNAL_UNAVAILABLE)
            return Ok(Secret(plaintext))

    async def write(self, path: str, value: Secret) -> Result[None, DomainError]:
        ct = self._fernet.encrypt(value.reveal().encode("utf-8"))
        async with self._session_factory() as session:
            existing = await session.get(SecretsStorage, path)
            if existing is None:
                session.add(SecretsStorage(path=path, ciphertext=ct))
            else:
                existing.ciphertext = ct
                existing.rotated_at = func.now()  # type: ignore[assignment]
            await session.commit()
        return Ok(None)

    async def delete(self, path: str) -> Result[None, DomainError]:
        async with self._session_factory() as session:
            await session.execute(delete(SecretsStorage).where(SecretsStorage.path == path))
            await session.commit()
        return Ok(None)
