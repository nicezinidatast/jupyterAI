"""Real-postgres integration for the credential-unit LocalKmsAdapter.

Verifies write → read returns the original plaintext, that the DB row contains
opaque ciphertext only, and that delete actually removes it.
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def test_write_then_read_returns_plaintext(fresh_session_factory) -> None:
    from credential.adapters.local_kms import LocalKmsAdapter
    from credential.models import SecretsStorage
    from dataplatform_shared.result import Ok
    from dataplatform_shared.security.secret import Secret

    key = Fernet.generate_key()
    adapter = LocalKmsAdapter(key=key, session_factory=fresh_session_factory)

    plain = "super-sekret-PA$$word-한글"
    write_result = await adapter.write("vault/itest/db1", Secret(plain))
    assert isinstance(write_result, Ok), write_result

    read_result = await adapter.read("vault/itest/db1")
    assert isinstance(read_result, Ok), read_result
    assert read_result.value.reveal() == plain

    # DB row must contain ciphertext only — never the plaintext.
    async with fresh_session_factory() as session:
        rows = (await session.execute(select(SecretsStorage))).scalars().all()
    assert len(rows) == 1
    assert plain.encode("utf-8") not in rows[0].ciphertext
    assert len(rows[0].ciphertext) > 0


async def test_read_missing_returns_not_found(fresh_session_factory) -> None:
    from credential.adapters.local_kms import LocalKmsAdapter
    from dataplatform_shared.errors import DomainError
    from dataplatform_shared.result import Err

    adapter = LocalKmsAdapter(key=Fernet.generate_key(), session_factory=fresh_session_factory)
    result = await adapter.read("vault/itest/missing")
    assert isinstance(result, Err)
    assert result.error == DomainError.NOT_FOUND


async def test_wrong_key_decryption_returns_external_unavailable(
    fresh_session_factory,
) -> None:
    """Two adapters with different keys — read with adapter B fails cleanly."""
    from credential.adapters.local_kms import LocalKmsAdapter
    from dataplatform_shared.errors import DomainError
    from dataplatform_shared.result import Err
    from dataplatform_shared.security.secret import Secret

    writer = LocalKmsAdapter(key=Fernet.generate_key(), session_factory=fresh_session_factory)
    await writer.write("vault/itest/cross", Secret("payload"))

    reader = LocalKmsAdapter(key=Fernet.generate_key(), session_factory=fresh_session_factory)
    result = await reader.read("vault/itest/cross")
    assert isinstance(result, Err)
    assert result.error == DomainError.EXTERNAL_UNAVAILABLE


async def test_overwrite_and_delete(fresh_session_factory) -> None:
    from credential.adapters.local_kms import LocalKmsAdapter
    from credential.models import SecretsStorage
    from dataplatform_shared.errors import DomainError
    from dataplatform_shared.result import Err, Ok
    from dataplatform_shared.security.secret import Secret

    adapter = LocalKmsAdapter(key=Fernet.generate_key(), session_factory=fresh_session_factory)
    await adapter.write("vault/itest/k", Secret("v1"))
    await adapter.write("vault/itest/k", Secret("v2"))

    read1 = await adapter.read("vault/itest/k")
    assert isinstance(read1, Ok)
    assert read1.value.reveal() == "v2"

    delete_result = await adapter.delete("vault/itest/k")
    assert isinstance(delete_result, Ok)

    after_delete = await adapter.read("vault/itest/k")
    assert isinstance(after_delete, Err)
    assert after_delete.error == DomainError.NOT_FOUND

    async with fresh_session_factory() as session:
        rows = (await session.execute(select(SecretsStorage))).scalars().all()
    assert rows == []
