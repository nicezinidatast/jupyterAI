"""PBT — the idempotency key is a pure function of its inputs."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from dataplatform_shared.idempotency import idempotency_key


@given(
    user=st.text(min_size=1, max_size=64),
    op=st.text(min_size=1, max_size=64),
    resource=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5),
)
def test_idempotency_is_deterministic(user: str, op: str, resource: dict[str, int]) -> None:
    """Equal inputs → equal keys (no time / random)."""
    assert idempotency_key(user, op, resource) == idempotency_key(user, op, resource)


@given(
    user=st.text(min_size=1, max_size=64),
    op=st.text(min_size=1, max_size=64),
)
def test_idempotency_dict_key_order_irrelevant(user: str, op: str) -> None:
    a = {"a": 1, "b": 2, "c": 3}
    b = {"c": 3, "a": 1, "b": 2}
    assert idempotency_key(user, op, a) == idempotency_key(user, op, b)


def test_idempotency_format() -> None:
    key = idempotency_key("u1", "register", {"x": 1})
    parts = key.split(":")
    assert parts[0] == "u1"
    assert parts[1] == "register"
    assert len(parts[2]) == 16
