"""공통 식별자 타입과 요청 전반에 전파되는 UserContext 정의."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NewType

# NewType을 쓰는 이유: 런타임 표현은 평범한 str/UUID 문자열로 두면서, 타입
# 검사기는 서로 다른 ID(예: UserId를 SessionId 자리에 넣는 실수)를 컴파일
# 시점에 잡아내게 한다. 런타임 비용 0의 "브랜드 타입(branded type)".
UserId = NewType("UserId", str)
SessionId = NewType("SessionId", str)
CorrelationId = NewType("CorrelationId", str)

# personas.md의 4가지 역할과 일치 (Q-USR-1=B,D). Literal이라 정의되지 않은
# 역할 문자열은 타입 검사기가 거부한다.
Role = Literal["Admin", "Analyst", "Viewer", "Auditor"]


@dataclass(frozen=True, slots=True)
class UserContext:
    """모든 도메인 호출에 전달되는 인증된 주체(principal).

    인증·인가·감사·상관관계 추적에 필요한 신원 정보를 한 묶음으로 운반한다.
    frozen이라 호출 체인 도중 변조될 수 없다(불변식: 한 요청 동안 신원 고정).
    ``corr_id``는 분산 추적·로그 상관(correlation)을 위한 요청 단위 식별자다.
    """

    user_id: UserId
    roles: tuple[Role, ...]
    session_id: SessionId
    corr_id: CorrelationId

    def has_role(self, role: Role) -> bool:
        return role in self.roles
