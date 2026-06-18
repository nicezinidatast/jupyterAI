"""슬라이딩 윈도우 레이트 리미터 (NFR-SL-SEC-03 / SECURITY-11).

핵심 불변식: 동시(concurrent) 호출자 둘이 동시에 ``count < limit``을 보고
둘 다 통과해 버리는 경쟁 조건(TOCTOU, Time-Of-Check to Time-Of-Use)을 막아야
한다. 그래서 구체 구현은 트림(오래된 항목 제거)/카운트/조건부 추가를 하나의
Redis Lua 스크립트로 원자적(atomic)으로 실행한다. Lua 스크립트는 Redis가
단일 스레드로 끊김 없이 실행하므로 중간에 다른 명령이 끼어들지 못한다.

Protocol을 둔 이유: 테스트에서 Redis 없이 가짜(fake) 리미터를 주입하기 위함.
"""

from __future__ import annotations

import time
from typing import Protocol


class RateLimiter(Protocol):
    """레이트 리미터 계약. 구현체는 키 단위로 허용 여부만 판정하면 된다."""

    async def check(self, key: str) -> bool:
        """허용이면 True, 한도 초과(rate-limited)면 False를 반환한다."""
        ...


class SlidingWindowLimiter:
    """Redis 기반 슬라이딩 윈도우. 버스트 부하에서 비원자적 파이프라인이
    노출할 TOCTOU 경쟁을 피하려고 Lua로 원자 실행한다.

    슬라이딩 윈도우 방식: 윈도우 안에 들어온 요청 타임스탬프를 정렬 집합(ZSET)에
    쌓고, 매 검사마다 윈도우보다 오래된 항목을 잘라낸 뒤 남은 개수로 판정한다.
    고정 윈도우(fixed window)와 달리 경계에서 순간 2배 폭주가 생기지 않는다.
    """

    # KEYS[1] = key, ARGV = (now_ms, window_ms, limit)
    # 스크립트 동작: ① 윈도우 밖(now - window 이전) 항목 제거 → ② 남은 개수 세기
    # → ③ limit 이상이면 0(거부) 반환 → ④ 아니면 현재 타임스탬프 추가 후 만료
    # 갱신하고 1(허용) 반환. ①~④가 한 호출 안에서 끊김 없이 실행돼 원자성 보장.
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
        # redis 클라이언트를 ``object``로 받아 덕 타이핑(duck typing)한다 — 테스트가
        # redis 패키지를 import하지 않고도 .eval만 흉내 낸 가짜를 넘길 수 있게.
        self._redis = redis_client
        self._limit = limit
        # 내부는 밀리초로 통일. Lua 스크립트가 ms 단위 타임스탬프를 다룬다.
        self._window_ms = window_seconds * 1000

    async def check(self, key: str) -> bool:
        now_ms = int(time.time() * 1000)
        # redis-py의 async 클라이언트는 첫 EVAL 이후 EVALSHA로 스크립트를 투명하게
        # 캐시하므로, 우리가 sha를 직접 관리하지 않아도 원자적 의미를 그대로 얻는다.
        allowed = await self._redis.eval(  # type: ignore[attr-defined]
            self._LUA_SCRIPT,
            1,
            key,
            str(now_ms),
            str(self._window_ms),
            str(self._limit),
        )
        return bool(int(allowed))
