"""속성 기반 테스트(PBT) — 멱등성 키가 입력만의 순수 함수임을 검증한다.

순수성·키 순서 무관·형식 세 성질을 무작위 입력으로 확인한다.
"""

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
    """같은 입력 → 같은 키 (시간·난수 의존 없음)."""
    assert idempotency_key(user, op, resource) == idempotency_key(user, op, resource)


@given(
    user=st.text(min_size=1, max_size=64),
    op=st.text(min_size=1, max_size=64),
)
def test_idempotency_dict_key_order_irrelevant(user: str, op: str) -> None:
    # 삽입 순서만 다른 같은 내용의 dict는 같은 키를 내야 한다(sort_keys 보장).
    a = {"a": 1, "b": 2, "c": 3}
    b = {"c": 3, "a": 1, "b": 2}
    assert idempotency_key(user, op, a) == idempotency_key(user, op, b)


def test_idempotency_format() -> None:
    key = idempotency_key("u1", "register", {"x": 1})
    parts = key.split(":")
    assert parts[0] == "u1"
    assert parts[1] == "register"
    assert len(parts[2]) == 16
