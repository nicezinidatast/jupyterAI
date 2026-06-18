"""단기 평문 캐시 (기본 TTL 60초).

Vault 호출마다 왕복 지연이 발생하는 것을 피하기 위해 인-프로세스 캐시를 둔다.
트레이드오프: 평문 시크릿이 메모리에 최대 TTL 동안 남는다는 공격 표면이 생긴다.
단, Vault의 감사 로그는 원본 ``read`` 시점을 그대로 기록하므로
캐시 히트 여부와 무관하게 최초 접근 이력은 보존된다.

rotate 또는 delete 후에는 반드시 invalidate를 호출해야 캐시가 구 시크릿을
계속 반환하는 문제를 방지할 수 있다 — CredentialVault 서비스가 이를 담당한다.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from uuid import UUID

from dataplatform_shared.security.secret import Secret


class ResolveCache:
    """credential_id → (Secret, 만료시각) 매핑을 유지하는 단기 인-프로세스 캐시.

    비동기 환경에서 두 코루틴이 동시에 같은 키를 갱신하는 것을 막기 위해 asyncio.Lock을 사용한다.
    단일 프로세스 내에서만 유효하며 다중 워커 배포 환경에서는 각 프로세스가 독립 캐시를 갖는다.
    """

    def __init__(self, *, ttl_seconds: int = 60) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._store: dict[UUID, tuple[Secret, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get_or_fetch(
        self, credential_id: UUID, fetcher: Callable[[], Awaitable[Secret]]
    ) -> Secret:
        """캐시에 유효한 항목이 있으면 반환하고, 없으면 fetcher를 호출해 채운다.

        fetcher 호출은 락 밖에서 이루어진다 — I/O 대기 중에 락을 잡아 두면
        다른 코루틴이 모두 블로킹되기 때문이다 (Read-then-write 패턴의 트레이드오프).
        """
        now = datetime.utcnow()
        async with self._lock:
            entry = self._store.get(credential_id)
            if entry and entry[1] > now:
                return entry[0]
        # 락을 해제한 후 Vault 조회 — 동일 키에 대한 중복 fetch가 드물게 발생할 수 있으나
        # 캐시 일관성 파괴는 아니다(마지막 write가 이기는 방식).
        secret = await fetcher()
        async with self._lock:
            self._store[credential_id] = (secret, now + self._ttl)
        return secret

    def invalidate(self, credential_id: UUID) -> None:
        """지정 credential의 캐시 항목을 즉시 제거한다.

        rotate/delete 직후에 호출해야 이후 resolve가 구 시크릿을 반환하지 않는다.
        """
        self._store.pop(credential_id, None)
