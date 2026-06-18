"""ShareLinkManager — "부여 권한 >= 요구 권한" 불변식을 강제한다.

핵심 보안 불변식: ``read`` 권한으로 발급된 공유 링크는 어떤 경우에도
``execute``나 ``edit``를 허용하면 안 된다. 토큰을 재전송(replay)하거나
요청을 반복해도 마찬가지다 — 권한 승격은 절대 일어나지 않는다.

접근 허용 조건은 두 가지를 모두 만족해야 한다.
1. 권한 등급: 링크의 권한이 요구 권한 이상(``_PERM_ORDER``로 비교).
2. 대상(audience) 일치: 요청자의 user_id 또는 요청자의 역할(role) 중 하나가
   링크에 등록된 대상에 포함.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.types.common import UserContext

from notebook.models import ShareAudience, ShareLink

# 권한을 정수 등급으로 매핑해 "이상/이하" 비교를 가능하게 한다.
# 숫자가 클수록 강한 권한: read(1) < execute(2) < edit(3).
Permission = Literal["read", "execute", "edit"]
_PERM_ORDER: dict[Permission, int] = {"read": 1, "execute": 2, "edit": 3}


@dataclass(frozen=True, slots=True)
class NotebookAccess:
    # 권한 검증을 통과했을 때 돌려주는 불변(frozen) 접근 결과.
    link_id: UUID
    notebook_id: UUID
    permission: Permission
    use_current_user_credentials: bool = True


class ShareLinkManager:
    """공유 링크 생성·폐기·해석(resolve)을 담당하는 서비스.

    상태를 들지 않고 주입된 세션에만 의존하므로 요청 단위로 생성해 쓴다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        notebook_id: UUID,
        permission: Permission,
        created_by: UUID,
        audience_users: tuple[UUID, ...] = (),
        audience_roles: tuple[str, ...] = (),
    ) -> Result[UUID, DomainError]:
        # 링크를 만들되 대상이 비어 있으면 거부한다 — 대상 없는 링크는
        # resolve에서 항상 FORBIDDEN이라 "아무도 못 쓰는 죽은 링크"가 되므로
        # 생성 단계에서 막는 편이 안전하다.
        if permission not in _PERM_ORDER:
            return Err(DomainError.VALIDATION)
        if not audience_users and not audience_roles:
            return Err(DomainError.VALIDATION)
        link_id = uuid4()
        self._session.add(
            ShareLink(
                link_id=link_id,
                notebook_id=notebook_id,
                permission=permission,
                created_by=created_by,
            )
        )
        # 대상은 user_id 행과 role 행으로 나눠 저장한다. 각 행은
        # (user_id XOR role) 불변식을 지켜 한쪽만 채운다(다른 쪽은 NULL).
        for u in audience_users:
            self._session.add(
                ShareAudience(link_id=link_id, subject_user_id=u, subject_role=None)
            )
        for r in audience_roles:
            self._session.add(
                ShareAudience(link_id=link_id, subject_user_id=None, subject_role=r)
            )
        await self._session.flush()
        return Ok(link_id)

    async def revoke(self, link_id: UUID) -> Result[None, DomainError]:
        from sqlalchemy import func as sql_func

        # 폐기는 행을 지우지 않고 revoked_at 타임스탬프를 찍는 소프트 삭제다.
        # 이미 폐기된 링크를 다시 폐기해도 시각을 덮어쓰지 않아 멱등하다.
        link = await self._session.get(ShareLink, link_id)
        if link is None:
            return Err(DomainError.NOT_FOUND)
        if link.revoked_at is None:
            link.revoked_at = sql_func.now()  # type: ignore[assignment]
        return Ok(None)

    async def resolve(
        self,
        link_id: UUID,
        requester: UserContext,
        required: Permission,
    ) -> Result[NotebookAccess, DomainError]:
        # 폐기됐거나 없는 링크는 "존재 여부"를 숨기려 NOT_FOUND로 통일한다.
        link = await self._session.get(ShareLink, link_id)
        if link is None or link.revoked_at is not None:
            return Err(DomainError.NOT_FOUND)
        # 불변식: 부여 권한이 요구 권한 이상이어야 한다. 이 비교가 곧
        # "read 링크로 execute를 못 얻는다"는 보안 보장의 핵심이다.
        if _PERM_ORDER[link.permission] < _PERM_ORDER[required]:
            return Err(DomainError.FORBIDDEN)

        # 대상 일치: 요청자의 UUID 또는 보유 역할 중 하나가 등록돼 있어야 한다.
        match_stmt = select(ShareAudience).where(ShareAudience.link_id == link_id)
        rows = (await self._session.execute(match_stmt)).scalars().all()
        # 대상이 한 행도 없으면 거부 — 무방비로 모두에게 열어 주지 않는다.
        if not rows:
            return Err(DomainError.FORBIDDEN)
        for row in rows:
            if row.subject_user_id and str(row.subject_user_id) == str(requester.user_id):
                return Ok(_to_access(link))
            if row.subject_role and row.subject_role in requester.roles:
                return Ok(_to_access(link))
        # 권한 등급은 충분해도 대상에 안 들면 접근 불가.
        return Err(DomainError.FORBIDDEN)


def _to_access(link: ShareLink) -> NotebookAccess:
    return NotebookAccess(
        link_id=link.link_id,
        notebook_id=link.notebook_id,
        permission=link.permission,  # type: ignore[arg-type]
        use_current_user_credentials=True,
    )
