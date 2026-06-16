"""PBT for Result helpers — exercises the monadic laws on Ok/Err."""

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
    # map_ok must not touch an Err value.
    e: Err[DomainError] = Err(err)
    assert map_ok(e, lambda v: v + 1) == e  # type: ignore[arg-type]


@pytest.mark.property
@given(st.integers())
def test_and_then_chain_associativity(value: int) -> None:
    # (Ok x).and_then(f).and_then(g) == (Ok x).and_then(lambda v: g(f(v).value))
    f = lambda v: Ok(v + 1)  # noqa: E731
    g = lambda v: Ok(v * 2)  # noqa: E731

    left = and_then(and_then(Ok(value), f), g)
    right = and_then(Ok(value), lambda v: g(unwrap(f(v))))
    assert left == right


def test_unwrap_err_raises() -> None:
    with pytest.raises(ValueError):
        unwrap(Err(DomainError.NOT_FOUND))


def test_is_ok_is_err() -> None:
    assert is_ok(Ok(1))
    assert not is_err(Ok(1))
    assert is_err(Err("oops"))
    assert not is_ok(Err("oops"))
