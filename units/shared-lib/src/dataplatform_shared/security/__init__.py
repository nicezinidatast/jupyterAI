"""보안 기본 요소: SecurityKernel 프로토콜, Secret 브랜드, 레이트 리미터.

모든 단위가 동일한 인증·인가 계약, 비밀값 누출 방지, 요청 폭주 차단 메커니즘을
공유하도록 한곳에 모은 패키지.
"""

from dataplatform_shared.security.kernel_iface import (
    Action,
    Decision,
    Resource,
    SecurityKernel,
)
from dataplatform_shared.security.rate_limit import RateLimiter, SlidingWindowLimiter
from dataplatform_shared.security.secret import SafeJSONEncoder, Secret

__all__ = [
    "SecurityKernel",
    "Action",
    "Resource",
    "Decision",
    "Secret",
    "SafeJSONEncoder",
    "RateLimiter",
    "SlidingWindowLimiter",
]
