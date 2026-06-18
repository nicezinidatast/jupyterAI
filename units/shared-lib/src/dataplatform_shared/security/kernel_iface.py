"""SecurityKernel 프로토콜 — 구체 구현은 gateway-unit에 있다.

여기에는 인터페이스(Protocol)만 둔다. shared-lib에 구체 구현을 두면 모든
단위가 게이트웨이 구현 세부에 의존하게 되므로, 계약만 노출하고 구현은 한
곳(gateway-unit)에 가두는 의존성 역전(dependency inversion)을 적용했다.
테스트는 이 Protocol을 만족하는 가짜(fake)를 주입할 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Result
from dataplatform_shared.types.common import UserContext

# 인가 검사 대상 동작. Literal이라 오타·미정의 동작을 타입 단계에서 막는다.
Action = Literal["read", "execute", "write", "admin"]


@dataclass(frozen=True, slots=True)
class Resource:
    """인가 대상 리소스. kind로 종류를, id로 특정 인스턴스를 가리킨다.

    id가 None이면 "해당 종류 전체"에 대한 검사(예: 모든 connection 읽기)다.
    """

    kind: Literal["connection", "notebook", "audit", "system", "credential", "share_link"]
    id: str | None = None


Decision = Literal["allow", "deny"]


class SecurityKernel(Protocol):
    """심층 방어(Defense in Depth, Q-AD-13=A) — 모든 도메인 진입점에서 호출한다.

    게이트웨이 한 곳에서만 막지 않고 각 도메인 진입점에서도 다시 검사하는
    이유는, 한 계층이 뚫려도 다음 계층이 막도록 방어선을 겹치기 위함이다.
    구현체가 지켜야 할 계약: 실패는 예외가 아니라 Err(DomainError)로 돌려준다.
    """

    async def authenticate(self, headers: dict[str, str]) -> Result[UserContext, DomainError]:
        """요청 헤더에서 UserContext(인증된 신원)를 해석해 반환한다."""
        ...

    async def authorize(
        self, ctx: UserContext, action: Action, resource: Resource
    ) -> Result[None, DomainError]:
        """허용이면 Ok, 아니면 Err(FORBIDDEN)을 반환한다.

        성공 시 의미 있는 값이 없으므로 Ok[None]을 쓴다 — "검사 통과" 자체가
        결과다.
        """
        ...
