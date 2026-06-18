"""credential-unit LocalKmsAdapter 의 실제 postgres 통합 테스트.

write → read 가 원본 평문을 반환하고, DB 행에는 불투명한 암호문만 저장되며,
delete 가 실제로 제거함을 검증한다.

LocalKmsAdapter 가 지켜야 할 보안 계약:
  - DB에 평문이 단 1바이트도 저장되지 않는다.
  - 다른 키로 복호화하면 NOT_FOUND 가 아닌 EXTERNAL_UNAVAILABLE 오류가 발생한다
    (키 불일치와 존재하지 않는 비밀을 구분한다).
  - 덮어쓰기와 삭제 후 읽기는 NOT_FOUND 를 반환한다.
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def test_write_then_read_returns_plaintext(fresh_session_factory) -> None:
    """쓰기 후 읽기가 원본 평문을 반환하고 DB 에는 암호문만 저장됨을 검증한다.

    한글 포함 평문을 사용해 유니코드 처리도 확인한다.
    DB 행에 평문 바이트가 포함되어 있으면 암호화가 적용되지 않은 것이다.
    """
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

    # DB 행에는 암호문만 있어야 한다 — 절대 평문이 포함되어서는 안 된다.
    async with fresh_session_factory() as session:
        rows = (await session.execute(select(SecretsStorage))).scalars().all()
    assert len(rows) == 1
    assert plain.encode("utf-8") not in rows[0].ciphertext
    assert len(rows[0].ciphertext) > 0


async def test_read_missing_returns_not_found(fresh_session_factory) -> None:
    """존재하지 않는 경로 읽기는 NOT_FOUND 오류를 반환한다.

    예외를 던지지 않고 Err(NOT_FOUND) 를 반환해야 호출자가 결과를 일관되게 처리할 수 있다.
    """
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
    """다른 키를 가진 두 어댑터: B 어댑터로 읽으면 EXTERNAL_UNAVAILABLE 오류가 반환된다.

    NOT_FOUND 와 구분하는 이유: 레코드는 존재하지만 키가 달라 복호화할 수 없는
    상황임을 호출자에게 알려야 한다(운영 설정 오류의 신호).
    """
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
    """덮어쓰기가 최신 값을 반환하고, 삭제 후 읽기는 NOT_FOUND 를 반환함을 검증한다.

    덮어쓰기: 동일 경로에 두 번 write 하면 마지막 값만 읽혀야 한다.
    삭제 후 DB 행이 완전히 제거되어야 한다(소프트 삭제 없음).
    """
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

    # DB 행이 실제로 제거되었는지 확인한다(소프트 삭제 없음).
    async with fresh_session_factory() as session:
        rows = (await session.execute(select(SecretsStorage))).scalars().all()
    assert rows == []
