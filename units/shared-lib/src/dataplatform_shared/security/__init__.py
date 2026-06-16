"""Security primitives: SecurityKernel protocol, Secret brand, rate limiter."""

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
