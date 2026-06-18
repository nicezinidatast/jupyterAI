"""도메인 코드용 Result / Either 타입 (Q-AD-5=A).

이 모듈은 함수형 언어의 Result(=Either) 모나드(monad, 값을 감싸 연쇄 가능한
컨테이너)를 파이썬으로 옮긴 것이다. 핵심 의도: "예상 가능한 실패"를 예외가
아니라 **반환값**으로 표현해, 호출자가 타입 시스템의 강제로 성공/실패를 반드시
다루게 한다.

- 모든 도메인 함수는 예상되는 결과에 대해 예외를 던지지 말고 `Result[T, E]`를
  반환해야 한다. 이렇게 하면 실패 경로가 시그니처에 드러나 누락되지 않는다.
- 반면 시스템 수준 장애(OOM, 디스크 풀 등 복구 불가능한 것)는 그대로 raise해도
  된다. 이런 예외는 fail-closed(실패 시 안전하게 막는) 전역 핸들러가 일반화된
  메시지로 변환한다 — 내부 정보 노출을 막기 위함.

`Ok`/`Err`는 frozen·slots dataclass라 불변(immutable)이며, 패턴 매칭과
`isinstance` 분기로 안전하게 갈라낸다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """값을 담은 성공 결과. 제네릭 T로 어떤 성공 타입이든 감쌀 수 있다."""

    value: T

    @property
    def ok(self) -> bool:  # noqa: D401 — short, simple property
        return True


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """에러를 담은 실패 결과. 제네릭 E로 도메인 에러 타입을 그대로 운반한다."""

    error: E

    @property
    def ok(self) -> bool:
        return False


# Result는 값을 든 Ok 또는 에러를 든 Err 둘 중 하나인 합 타입(union).
# TypeAlias로 두 제네릭을 한 이름에 묶어 시그니처를 Result[T, E]로 간결하게 쓴다.
Result: TypeAlias = Ok[T] | Err[E]


def map_ok(result: Result[T, E], fn: Callable[[T], U]) -> Result[U, E]:
    """Ok면 그 안의 값에 fn을 적용해 새 Ok로, Err면 그대로 통과시킨다.

    모나드의 functor map에 해당한다. 에러를 건드리지 않고 성공 값만 변환하므로
    실패 경로가 자동으로 보존된다(Err 단락 효과).
    """
    if isinstance(result, Ok):
        return Ok(fn(result.value))
    return result


def and_then(result: Result[T, E], fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
    """Ok면 Result를 반환하는 fn으로 연쇄하고, Err면 즉시 단락(short-circuit)한다.

    모나드의 bind(flatMap)에 해당한다. fn 자체가 Err를 낼 수 있는 다단계 검증을
    이어 붙일 때, 첫 실패에서 멈추고 그 Err를 그대로 전파하는 것이 핵심 가치다.
    """
    if isinstance(result, Ok):
        return fn(result.value)
    return result


def unwrap(result: Result[T, E]) -> T:
    """Ok 값을 꺼내거나, Err면 ``ValueError``를 던진다.

    Err를 만나면 강제 실패(hard-fail)하므로 일반 도메인 경로에서는 쓰지 말 것.
    테스트 코드나, 반드시 실패해야 하는 경계(boundary)에서만 사용한다.
    """
    if isinstance(result, Ok):
        return result.value
    raise ValueError(f"unwrap on Err: {result.error!r}")


# 아래 두 함수는 호출부에서 isinstance를 직접 쓰지 않고 의도를 드러내는 술어
# (predicate)다. 타입 가드로도 쓰여 분기 후 타입 좁히기에 도움이 된다.
def is_ok(result: Result[T, E]) -> bool:
    return isinstance(result, Ok)


def is_err(result: Result[T, E]) -> bool:
    return isinstance(result, Err)
