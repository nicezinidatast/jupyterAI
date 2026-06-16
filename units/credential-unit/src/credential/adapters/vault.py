"""Vault adapter — wraps hvac so domain code stays Vault-agnostic.

A Protocol is exposed so tests can pass an in-memory fake.
"""

from __future__ import annotations

from typing import Protocol

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret


class VaultAdapter(Protocol):
    async def read(self, path: str) -> Result[Secret, DomainError]: ...
    async def write(self, path: str, value: Secret) -> Result[None, DomainError]: ...
    async def delete(self, path: str) -> Result[None, DomainError]: ...


class InMemoryVaultAdapter:
    """Test/dev double — keeps secrets in a dict.

    Production deployments wire ``HvacVaultAdapter`` (see below).
    """

    def __init__(self) -> None:
        self._store: dict[str, Secret] = {}

    async def read(self, path: str) -> Result[Secret, DomainError]:
        if path not in self._store:
            return Err(DomainError.NOT_FOUND)
        return Ok(self._store[path])

    async def write(self, path: str, value: Secret) -> Result[None, DomainError]:
        self._store[path] = value
        return Ok(None)

    async def delete(self, path: str) -> Result[None, DomainError]:
        self._store.pop(path, None)
        return Ok(None)


class HvacVaultAdapter:
    """Production adapter backed by HashiCorp Vault KV v2.

    Imports ``hvac`` lazily so tests don't need it.
    """

    def __init__(self, *, addr: str, token: Secret, mount: str = "secret") -> None:
        import hvac  # noqa: PLC0415 — lazy import

        self._client = hvac.Client(url=addr, token=token.reveal())
        self._mount = mount

    async def read(self, path: str) -> Result[Secret, DomainError]:
        try:
            data = self._client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self._mount
            )
        except Exception:  # noqa: BLE001 — hvac may raise various concrete types
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        try:
            value = data["data"]["data"]["value"]
        except (KeyError, TypeError):
            return Err(DomainError.NOT_FOUND)
        return Ok(Secret(value))

    async def write(self, path: str, value: Secret) -> Result[None, DomainError]:
        try:
            self._client.secrets.kv.v2.create_or_update_secret(
                path=path, secret={"value": value.reveal()}, mount_point=self._mount
            )
            return Ok(None)
        except Exception:  # noqa: BLE001
            return Err(DomainError.EXTERNAL_UNAVAILABLE)

    async def delete(self, path: str) -> Result[None, DomainError]:
        try:
            self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path, mount_point=self._mount
            )
            return Ok(None)
        except Exception:  # noqa: BLE001
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
