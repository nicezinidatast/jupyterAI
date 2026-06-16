"""CredentialVault — register / rotate / delete / resolve."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret
from dataplatform_shared.types.common import UserContext

from credential.adapters.vault import VaultAdapter
from credential.cache import ResolveCache
from credential.models import Credential


class CredentialVault:
    def __init__(
        self,
        *,
        session: AsyncSession,
        vault: VaultAdapter,
        cache: ResolveCache | None = None,
    ) -> None:
        self._session = session
        self._vault = vault
        self._cache = cache or ResolveCache()

    async def register(
        self,
        *,
        scope: str,
        name: str,
        secret: Secret,
        owner_user_id: UUID | None = None,
    ) -> Result[UUID, DomainError]:
        if scope not in ("shared", "personal"):
            return Err(DomainError.VALIDATION)
        if scope == "personal" and owner_user_id is None:
            return Err(DomainError.VALIDATION)
        if scope == "shared" and owner_user_id is not None:
            return Err(DomainError.VALIDATION)

        credential_id = uuid4()
        path = self._build_path(scope, owner_user_id, credential_id)
        row = Credential(
            credential_id=credential_id,
            scope=scope,
            owner_user_id=owner_user_id,
            name=name,
            vault_path=path,
            is_active=True,
        )
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError:
            return Err(DomainError.CONFLICT)
        write = await self._vault.write(path, secret)
        if not write.ok:
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        return Ok(credential_id)

    async def rotate(self, credential_id: UUID, new_secret: Secret) -> Result[None, DomainError]:
        row = await self._session.get(Credential, credential_id)
        if row is None or row.deleted_at is not None:
            return Err(DomainError.NOT_FOUND)
        write = await self._vault.write(row.vault_path, new_secret)
        if not write.ok:
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        self._cache.invalidate(credential_id)
        from sqlalchemy import func as sql_func

        row.rotated_at = sql_func.now()  # type: ignore[assignment]
        return Ok(None)

    async def delete(self, credential_id: UUID) -> Result[None, DomainError]:
        row = await self._session.get(Credential, credential_id)
        if row is None or row.deleted_at is not None:
            return Err(DomainError.NOT_FOUND)
        from sqlalchemy import func as sql_func

        row.deleted_at = sql_func.now()  # type: ignore[assignment]
        row.is_active = False
        await self._vault.delete(row.vault_path)
        self._cache.invalidate(credential_id)
        return Ok(None)

    async def resolve(
        self, credential_id: UUID, requester: UserContext
    ) -> Result[Secret, DomainError]:
        row = await self._session.get(Credential, credential_id)
        if row is None or row.deleted_at is not None:
            return Err(DomainError.NOT_FOUND)
        if row.scope == "personal" and str(row.owner_user_id) != str(requester.user_id):
            return Err(DomainError.FORBIDDEN)
        # shared credentials rely on connection grants checked by data-unit
        async def fetch() -> Secret:
            result = await self._vault.read(row.vault_path)
            if not result.ok:
                # Cache layer can't return Result; raise so caller's Err path picks up.
                raise LookupError(result.error)
            return result.value

        try:
            secret = await self._cache.get_or_fetch(credential_id, fetch)
        except LookupError as e:  # noqa: BLE001
            err = e.args[0] if e.args else DomainError.EXTERNAL_UNAVAILABLE
            return Err(err)
        return Ok(secret)

    @staticmethod
    def _build_path(scope: str, owner_user_id: UUID | None, credential_id: UUID) -> str:
        if scope == "shared":
            return f"dataplatform/shared/{credential_id}"
        return f"dataplatform/personal/{owner_user_id}/{credential_id}"
