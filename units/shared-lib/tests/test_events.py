"""DomainEvent round-trip + Secret rejection."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dataplatform_shared.audit.events import make_event
from dataplatform_shared.security.secret import Secret


def test_make_event_basic() -> None:
    e = make_event(
        type="login",
        actor="u-1",
        result="success",
        corr_id="cid-1",
        resource="session:abc",
        payload={"ip": "10.0.0.1"},
        at=datetime(2026, 5, 21, 0, 0, 0, tzinfo=UTC),
    )
    assert e["type"] == "login"
    assert e["actor"] == "u-1"
    assert e["result"] == "success"
    assert e["at"].endswith("+00:00")


def test_make_event_rejects_secret_in_payload() -> None:
    with pytest.raises(ValueError, match="Secret"):
        make_event(
            type="x",
            actor="u",
            result="success",
            corr_id="c",
            payload={"pw": Secret("hunter2")},
        )


def test_make_event_rejects_nested_secret() -> None:
    with pytest.raises(ValueError, match="Secret"):
        make_event(
            type="x",
            actor="u",
            result="success",
            corr_id="c",
            payload={"creds": {"pw": Secret("hunter2")}},
        )


@given(
    type_=st.text(min_size=1, max_size=32),
    actor=st.text(min_size=1, max_size=32),
    result=st.sampled_from(["success", "failure"]),
    corr_id=st.text(min_size=1, max_size=32),
)
def test_make_event_round_trip(type_: str, actor: str, result: str, corr_id: str) -> None:
    """make_event → json → dict yields the same data (modulo string typing)."""
    e = make_event(
        type=type_, actor=actor, result=result, corr_id=corr_id, payload={"k": 1}
    )
    blob = json.dumps(e)
    parsed = json.loads(blob)
    assert parsed["type"] == type_
    assert parsed["actor"] == actor
    assert parsed["result"] == result
    assert parsed["corr_id"] == corr_id
    assert parsed["payload"] == {"k": 1}
