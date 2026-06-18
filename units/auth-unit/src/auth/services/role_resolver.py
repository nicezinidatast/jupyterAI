"""'활성 Admin이 최소 1명' 불변식을 지키는 역할 부여(US-AUTH-02).

이 불변식이 깨지면 아무도 시스템을 관리할 수 없는 잠금(lockout) 상태가 된다.
따라서 마지막 Admin을 제거하려는 시도는 조용히 통과시키지 않고 명시적으로
거부한다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result

from auth.models import User, UserRole, VALID_ROLES


class RoleResolver:
    """사용자 ↔ 역할 매핑을 관리한다.

    불변식: 'Admin' 역할을 가진 활성 사용자가 항상 ≥ 1명이다. 위반 시 시스템을
    조용히 잠금 상태로 두지 않고 ``Err(CONFLICT)``를 반환한다. 모든 메서드는
    예외 대신 ``Result``를 돌려주어, 호출자가 성공/실패를 타입 차원에서 반드시
    다루게 한다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_roles(self, user_id: UUID) -> Result[tuple[str, ...], DomainError]:
        rows = await self._session.scalars(
            select(UserRole.role).where(UserRole.user_id == user_id)
        )
        return Ok(tuple(rows.all()))

    async def assign_role(
        self, target_user_id: UUID, role: str
    ) -> Result[None, DomainError]:
        if role not in VALID_ROLES:
            return Err(DomainError.VALIDATION)
        # 멱등(idempotent) — 이미 있는 역할을 다시 부여하면 아무 일도 하지 않는다.
        # 같은 부여를 두 번 호출해도 안전하므로 호출부에서 중복 검사를 안 해도 된다.
        existing = await self._session.scalar(
            select(UserRole).where(
                and_(UserRole.user_id == target_user_id, UserRole.role == role)
            )
        )
        if existing is None:
            self._session.add(UserRole(user_id=target_user_id, role=role))
            await self._session.flush()
        return Ok(None)

    async def revoke_role(
        self, target_user_id: UUID, role: str
    ) -> Result[None, DomainError]:
        if role not in VALID_ROLES:
            return Err(DomainError.VALIDATION)

        if role == "Admin":
            # *다른* 활성 admin 행들을 잠근다. 잠그지 않으면 동시에 들어온 두 요청이
            # 각자 "다른 admin이 1명 있다"고 관찰하고 둘 다 진행해, 결과적으로 admin이
            # 0명이 되는 경쟁 조건(race condition)이 생긴다. ``FOR UPDATE``는 Postgres
            # 에서 이 카운트를 직렬화한다(한 트랜잭션이 잠그면 다른 쪽은 대기). sqlite
            # (테스트 픽스처)는 이 절을 조용히 무시하지만, sqlite는 어차피 단일 writer
            # 라 같은 보호가 성립한다.
            lock_stmt = (
                select(UserRole.user_id)
                .join(User, User.user_id == UserRole.user_id)
                .where(
                    and_(
                        UserRole.role == "Admin",
                        UserRole.user_id != target_user_id,
                        User.is_active.is_(True),
                    )
                )
            )
            try:
                lock_stmt = lock_stmt.with_for_update()
            except Exception:  # pragma: no cover — FOR UPDATE를 지원하지 않는 방언
                # FOR UPDATE 미지원 방언이면 잠금 없이 진행한다 — 단일 writer 환경을
                # 가정한 대비이므로 정확성은 유지된다.
                pass
            other_admin_ids = (await self._session.execute(lock_stmt)).scalars().all()
            # 대상 외에 활성 admin이 한 명도 없으면, 이 취소는 마지막 admin을 없애므로 거부.
            if len(other_admin_ids) < 1:
                return Err(DomainError.CONFLICT)

        await self._session.execute(
            delete(UserRole).where(
                and_(UserRole.user_id == target_user_id, UserRole.role == role)
            )
        )
        return Ok(None)
