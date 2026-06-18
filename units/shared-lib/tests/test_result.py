"""Result 헬퍼에 대한 속성 기반 테스트(PBT).

PBT(Property-Based Testing): 특정 예시가 아니라 "임의의 입력 전반에서 성립해야
하는 성질"을 검증한다. 여기서는 Ok/Err에 대한 모나드 법칙(map 항등성,
bind 결합성 등)을 hypothesis가 만든 무작위 입력으로 확인한다.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import (
    Err,
    Ok,
    and_then,
    is_err,
    is_ok,
    map_ok,
    unwrap,
)


@given(st.integers())
def test_map_ok_on_ok(value: int) -> None:
    assert map_ok(Ok(value), lambda v: v + 1) == Ok(value + 1)


@given(st.sampled_from(list(DomainError)))
def test_map_ok_on_err_is_identity(err: DomainError) -> None:
    # map_ok은 Err 값을 절대 건드리지 않아야 한다(Err에 대해 항등 함수).
    e: Err[DomainError] = Err(err)
    assert map_ok(e, lambda v: v + 1) == e  # type: ignore[arg-type]


@pytest.mark.property
@given(st.integers())
def test_and_then_chain_associativity(value: int) -> None:
    # 모나드 결합 법칙(associativity)을 확인한다:
    # (Ok x).and_then(f).and_then(g) == (Ok x).and_then(lambda v: g(f(v).value))
    f = lambda v: Ok(v + 1)  # noqa: E731
    g = lambda v: Ok(v * 2)  # noqa: E731

    left = and_then(and_then(Ok(value), f), g)
    right = and_then(Ok(value), lambda v: g(unwrap(f(v))))
    assert left == right


def test_unwrap_err_raises() -> None:
    # unwrap은 Err에서 강제 실패해야 한다 — 조용히 None을 돌려주면 안 됨.
    with pytest.raises(ValueError):
        unwrap(Err(DomainError.NOT_FOUND))


def test_is_ok_is_err() -> None:
    # 두 술어가 서로 배타적임을 확인(Ok면 is_err False, Err면 is_ok False).
    assert is_ok(Ok(1))
    assert not is_err(Ok(1))
    assert is_err(Err("oops"))
    assert not is_ok(Err("oops"))
