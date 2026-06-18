"""CredentialVault 서비스 — register / rotate / delete / resolve 네 가지 상태 전이를 담당한다.

설계 원칙:
  - 메타데이터(이름·스코프·경로)는 DB의 Credential 행에, 평문 시크릿은 Vault에 분리 보관한다.
  - 두 저장소 간 쓰기 순서: DB flush 성공 후 Vault write. 반대로 하면
    Vault에만 데이터가 남고 DB에 참조가 없는 고아(orphan) 시크릿이 생길 수 있다.
  - 외부 노출 타입은 Result[T, DomainError]로 통일 — 예외를 값으로 변환해 호출자가
    오류 경로를 강제로 처리하도록 한다.
"""

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
    """자격증명(Credential)의 전체 생애주기를 관리하는 도메인 서비스.

    session: 단일 요청 트랜잭션 범위의 SQLAlchemy 비동기 세션.
    vault: Vault 저장소 어댑터 (HvacVaultAdapter 또는 LocalKmsAdapter).
    cache: 인-프로세스 단기 캐시 (None이면 기본값 ResolveCache 생성).
    """

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
        """새 Credential을 등록한다.

        불변식:
          - shared 스코프는 owner_user_id가 없어야 한다.
          - personal 스코프는 owner_user_id가 있어야 한다.
          - (scope, owner_user_id, name) 조합은 유일해야 한다 — 위반 시 CONFLICT 반환.

        쓰기 순서: DB flush → Vault write.
        DB flush 실패(IntegrityError)가 먼저 감지되므로 Vault에 고아 시크릿이 남는 경우를 줄인다.
        반대로 Vault write 실패 시에는 DB 행이 커밋 전 상태이므로 세션 롤백으로 자동 제거된다.
        """
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
            # uq_cred_name 제약 위반 — 동일 (scope, owner, name) 조합 중복 등록 시도.
            return Err(DomainError.CONFLICT)
        write = await self._vault.write(path, secret)
        if not write.ok:
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        return Ok(credential_id)

    async def rotate(self, credential_id: UUID, new_secret: Secret) -> Result[None, DomainError]:
        """Vault의 시크릿을 교체하고 캐시를 무효화한다.

        삭제된(deleted_at 설정된) Credential에 대한 rotate는 NOT_FOUND로 거부한다.
        캐시 무효화는 Vault write 성공 후에 수행한다 — write 실패 시 캐시를 건드리지 않는다.
        """
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
        """Credential을 소프트 삭제(soft delete)하고 Vault에서 시크릿을 제거한다.

        deleted_at 타임스탬프를 기록하고 is_active를 False로 전환 — 물리 삭제 없이
        이력을 보존한다. Vault delete는 best-effort로 호출하며 실패해도 메타데이터는
        삭제 완료로 처리한다(고아 시크릿 가능성 허용, 트레이드오프).
        """
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
        """Credential의 평문 시크릿을 반환한다.

        접근 제어:
          - personal Credential은 owner_user_id와 requester.user_id가 일치해야 한다.
          - shared Credential의 접근 권한은 data-unit의 connection grant로 별도 검증한다.

        ResolveCache를 거쳐 Vault 호출을 최소화한다. 캐시 미스 시에만 Vault에
        실제 요청이 발생한다. Cache.get_or_fetch는 Result를 받지 못하므로 Vault
        오류를 LookupError로 감싸 전달하고 여기서 다시 Err로 변환한다.
        """
        row = await self._session.get(Credential, credential_id)
        if row is None or row.deleted_at is not None:
            return Err(DomainError.NOT_FOUND)
        if row.scope == "personal" and str(row.owner_user_id) != str(requester.user_id):
            return Err(DomainError.FORBIDDEN)
        # shared Credential의 접속 권한은 data-unit의 connection grant로 별도 검증한다.
        async def fetch() -> Secret:
            result = await self._vault.read(row.vault_path)
            if not result.ok:
                # 캐시 레이어는 Result를 반환할 수 없으므로 예외로 전달한다.
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
        """Vault/DB 저장 경로를 결정한다.

        경로 구조:
          - shared: dataplatform/shared/<credential_id>
          - personal: dataplatform/personal/<owner_user_id>/<credential_id>
        personal 경로에 owner_user_id를 포함하는 이유: Vault ACL 정책을
        경로 접두사 기반으로 설정할 수 있어 per-user 격리가 용이하기 때문이다.
        """
        if scope == "shared":
            return f"dataplatform/shared/{credential_id}"
        return f"dataplatform/personal/{owner_user_id}/{credential_id}"
