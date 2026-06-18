"""RoleResolver 위의 얇은 조율 계층 — 다른 단위들이 접근 권한을 확인할 때 쓴다.

권한 검사의 단일 진입점을 제공해, 각 단위가 역할-정책 매핑을 제각각 복제하지
않도록 한다. 자원 수준의 세밀한 정책(연결 권한 부여, 공유 링크 대상 등)은 해당
자원을 소유한 단위가 따로 평가한다.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.kernel_iface import Action, Resource
from dataplatform_shared.types.common import UserContext

from auth.services.role_resolver import RoleResolver

# 거친(coarse) 역할 정책. (동작, 자원종류) → 허용 역할 집합의 매핑이다. 자원
# 수준 정책(연결 권한 부여, 공유 링크 대상)은 소유 단위(data-unit / notebook-unit)
# 가 평가한다. 여기 없는 조합은 기본 거부되므로(아래 fail-closed) 명시된 항목이
# 곧 허용 목록(allow-list)이다.
_ROLE_POLICY: dict[tuple[Action, str], frozenset[str]] = {
    ("admin", "system"): frozenset({"Admin"}),
    ("read", "audit"): frozenset({"Admin", "Auditor"}),
    ("write", "audit"): frozenset(),  # 감사 로그는 누구도 직접 쓰지 않는다(빈 집합 = 전원 거부)
    ("read", "connection"): frozenset({"Admin", "Analyst", "Auditor"}),
    ("execute", "connection"): frozenset({"Admin", "Analyst"}),
    ("read", "notebook"): frozenset({"Admin", "Analyst", "Viewer"}),
    ("write", "notebook"): frozenset({"Admin", "Analyst"}),
}


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._roles = RoleResolver(session)

    async def verify_access(
        self, ctx: UserContext, action: Action, resource: Resource
    ) -> Result[None, DomainError]:
        allowed = _ROLE_POLICY.get((action, resource.kind))
        if allowed is None:
            # 정의되지 않은 (동작, 자원) 조합은 기본 거부한다(fail-closed,
            # SECURITY-15). 정책 누락을 우발적 허용으로 두지 않기 위함이다.
            return Err(DomainError.FORBIDDEN)
        # 사용자의 역할 중 하나라도 허용 집합에 들면 통과(역할은 여러 개일 수 있음).
        if not any(r in allowed for r in ctx.roles):
            return Err(DomainError.FORBIDDEN)
        return Ok(None)

    async def change_role(
        self, target: UUID, role: str, op: str
    ) -> Result[None, DomainError]:
        # op 문자열로 부여/취소를 분기. 알 수 없는 op는 VALIDATION 오류로 막아
        # 잘못된 호출이 조용히 무시되지 않게 한다.
        if op == "assign":
            return await self._roles.assign_role(target, role)
        if op == "revoke":
            return await self._roles.revoke_role(target, role)
        return Err(DomainError.VALIDATION)
