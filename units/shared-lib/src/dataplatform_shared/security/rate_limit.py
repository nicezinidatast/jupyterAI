"""Sliding-window rate limiter (NFR-SL-SEC-03 / SECURITY-11).

The concrete implementation runs the trim/count/conditional-add as a single
Redis Lua script so concurrent callers cannot both observe ``count < limit``
and both succeed. The Protocol lets units inject a fake during tests.
"""

from __future__ import annotations

import time
from typing import Protocol


class RateLimiter(Protocol):
    async def check(self, key: str) -> bool:
        """Return True if the request is allowed; False if rate-limited."""
        ...


class SlidingWindowLimiter:
    """Redis-backed sliding window. Atomic via Lua to avoid the TOCTOU race
    that a non-atomic pipeline would expose under burst load."""

    # KEYS[1] = key, ARGV = (now_ms, window_ms, limit)
    _LUA_SCRIPT = """
        local cutoff = tonumber(ARGV[1]) - tonumber(ARGV[2])
        redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, cutoff)
        local count = redis.call('ZCARD', KEYS[1])
        if count >= tonumber(ARGV[3]) then
            return 0
        end
        redis.call('ZADD', KEYS[1], ARGV[1], ARGV[1])
        redis.call('PEXPIRE', KEYS[1], ARGV[2])
        return 1
    """

    def __init__(self, redis_client: object, *, limit: int, window_seconds: int) -> None:
        # Accept the redis client by duck-type so tests can pass a fake without
        # importing redis itself.
        self._redis = redis_client
        self._limit = limit
        self._window_ms = window_seconds * 1000

    async def check(self, key: str) -> bool:
        now_ms = int(time.time() * 1000)
        # redis-py's async client caches the script transparently after the
        # first EVAL via EVALSHA, so we get atomic semantics without managing
        # the sha ourselves.
        allowed = await self._redis.eval(  # type: ignore[attr-defined]
            self._LUA_SCRIPT,
            1,
            key,
            str(now_ms),
            str(self._window_ms),
            str(self._limit),
        )
        return bool(int(allowed))
