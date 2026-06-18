"""로컬 KMS Vault 어댑터 — Fernet 암호화 + DB 영속 저장.

HashiCorp Vault 없이 폐쇄망에서 운영하기 위한 프로덕션 수준의 대체 경로다.
Fernet 키는 백엔드 프로세스의 환경 변수 ``BACKEND_CREDENTIAL_KEY`` 에만
존재한다. DB에는 불투명한 암호문(ciphertext)만 저장되고 평문은 절대 기록되지
않는다.

이 어댑터는 :class:`credential.adapters.vault.VaultAdapter` Protocol을 구현하며
``HvacVaultAdapter`` 의 드롭인 교체품이다.

보안 트레이드오프:
- 키가 유출되면 모든 시크릿이 복호화 가능하다 → 키 로테이션 절차가 필수다.
- Vault와 달리 감사 로그(audit trail)가 DB 레이어에 없다 → 변경 이력은 애플리케이션
  레이어의 rotate/delete 이벤트에 의존한다.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import delete, func

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret

from credential.models import SecretsStorage


class LocalKmsAdapter:
    """Fernet(AES-128-CBC + HMAC-SHA256) 암호화 + DB 영속을 조합한 Vault 대체 어댑터.

    AES 기반 대칭키 암호화 라이브러리인 Fernet은 평문에 타임스탬프와 HMAC을 포함하므로
    암호문 변조 감지가 내장되어 있다. 잘못된 키로 복호화를 시도하면 InvalidToken을 던진다.
    """

    def __init__(self, *, key: bytes, session_factory) -> None:
        # Fernet은 생성자에서 키 형식(32바이트 url-safe base64)을 검증한다.
        # 잘못된 키를 전달하면 여기서 즉시 예외가 발생하므로 런타임에 조용히 실패하지 않는다.
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
                # 키 불일치 또는 암호문 변조 시 발생한다.
                # EXTERNAL_UNAVAILABLE로 매핑해 키 로테이션 문제임을 운영팀에 알린다.
                return Err(DomainError.EXTERNAL_UNAVAILABLE)
            return Ok(Secret(plaintext))

    async def write(self, path: str, value: Secret) -> Result[None, DomainError]:
        ct = self._fernet.encrypt(value.reveal().encode("utf-8"))
        async with self._session_factory() as session:
            existing = await session.get(SecretsStorage, path)
            if existing is None:
                session.add(SecretsStorage(path=path, ciphertext=ct))
            else:
                # 기존 행을 업데이트하고 로테이션 시각을 기록한다.
                # upsert가 아닌 get → 분기 방식을 쓰는 이유: 로테이션 여부를
                # rotated_at으로 구분해야 하기 때문이다.
                existing.ciphertext = ct
                existing.rotated_at = func.now()  # type: ignore[assignment]
            await session.commit()
        return Ok(None)

    async def delete(self, path: str) -> Result[None, DomainError]:
        async with self._session_factory() as session:
            # 행이 없어도 에러를 내지 않아 멱등(idempotent) delete가 보장된다.
            await session.execute(delete(SecretsStorage).where(SecretsStorage.path == path))
            await session.commit()
        return Ok(None)
