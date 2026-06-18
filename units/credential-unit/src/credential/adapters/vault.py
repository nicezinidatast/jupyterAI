"""Vault 어댑터 — hvac를 감싸 도메인 코드가 Vault 구현에 의존하지 않도록 한다.

Protocol을 노출하므로 테스트는 인메모리 페이크를 주입할 수 있다.
이 파일이 정의하는 VaultAdapter Protocol이 credential-unit 전체의 시크릿
저장소 계약(contract)이다. 실제 구현은 두 가지:
  - HvacVaultAdapter: HashiCorp Vault KV v2 (외부 Vault 운영 환경)
  - LocalKmsAdapter (local_kms.py): Fernet + DB (폐쇄망 환경)
"""

from __future__ import annotations

from typing import Protocol

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret


class VaultAdapter(Protocol):
    """시크릿 저장소 추상화 계약.

    이 Protocol을 구현하는 클래스는 경로(path)를 키로 Secret을 읽고 쓰고 지운다.
    반환 타입이 Result이므로 예외가 아니라 값으로 오류를 전달한다 — 호출자가
    모든 오류 경로를 컴파일 시점에 처리하도록 강제하는 트레이드오프다.
    """

    async def read(self, path: str) -> Result[Secret, DomainError]: ...
    async def write(self, path: str, value: Secret) -> Result[None, DomainError]: ...
    async def delete(self, path: str) -> Result[None, DomainError]: ...


class InMemoryVaultAdapter:
    """테스트/개발용 페이크 — 시크릿을 dict에 보관한다.

    프로덕션에서는 HvacVaultAdapter 또는 LocalKmsAdapter를 연결한다.
    인메모리이므로 프로세스 재시작 시 데이터가 사라진다는 점에 유의한다.
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
        # pop은 키가 없어도 예외를 발생시키지 않으므로 멱등(idempotent) delete가 된다.
        self._store.pop(path, None)
        return Ok(None)


class HvacVaultAdapter:
    """HashiCorp Vault KV v2 기반 프로덕션 어댑터.

    hvac를 지연 임포트하는 이유: 테스트 환경에 hvac가 설치되지 않아도
    이 모듈을 임포트할 수 있어야 하기 때문이다.

    token은 Secret 타입으로 받아 .reveal()로만 평문에 접근한다 — 로그나
    repr에 토큰이 노출되는 것을 방지하기 위함이다.
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
        except Exception:  # noqa: BLE001 — hvac가 다양한 구체 타입을 던질 수 있어 넓게 잡는다
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        try:
            # KV v2 응답 구조: data.data.data.value
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
            # delete_metadata_and_all_versions는 모든 버전 이력까지 삭제한다.
            # 단순 soft-delete가 아니라 KV v2의 메타데이터까지 완전 제거된다.
            self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path, mount_point=self._mount
            )
            return Ok(None)
        except Exception:  # noqa: BLE001
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
