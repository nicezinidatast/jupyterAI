"""모든 단위가 공유하는 공통 타입 별칭 패키지.

식별자 타입과 요청 전반에 전파되는 UserContext를 한곳에 모아, 각 단위가
같은 신원(identity) 모델을 쓰게 보장한다.
"""

from dataplatform_shared.types.common import (
    CorrelationId,
    Role,
    SessionId,
    UserContext,
    UserId,
)

__all__ = ["UserId", "Role", "CorrelationId", "SessionId", "UserContext"]
