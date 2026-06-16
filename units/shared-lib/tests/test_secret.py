"""Secret brand must never render its plaintext via repr/str/format/pickle/SafeJSON."""

from __future__ import annotations

import json
import pickle

import pytest

from dataplatform_shared.security.secret import SafeJSONEncoder, Secret


def test_repr_redacted() -> None:
    s = Secret("hunter2")
    assert "hunter2" not in repr(s)
    assert "REDACTED" in repr(s)


def test_str_redacted() -> None:
    s = Secret("hunter2")
    assert "hunter2" not in str(s)


def test_format_redacted() -> None:
    s = Secret("hunter2")
    assert "hunter2" not in f"{s}"
    assert "hunter2" not in f"{s!s}"


def test_pickle_refused() -> None:
    s = Secret("hunter2")
    with pytest.raises(TypeError, match="Secret"):
        pickle.dumps(s)


def test_safe_json_top_level() -> None:
    s = Secret("hunter2")
    with pytest.raises(TypeError, match="Secret"):
        json.dumps(s, cls=SafeJSONEncoder)


def test_safe_json_nested_dict() -> None:
    payload = {"creds": {"pw": Secret("hunter2"), "user": "alice"}}
    with pytest.raises(TypeError, match="Secret"):
        json.dumps(payload, cls=SafeJSONEncoder)


def test_safe_json_in_list() -> None:
    payload = {"creds": ["a", Secret("hunter2"), "b"]}
    with pytest.raises(TypeError, match="Secret"):
        json.dumps(payload, cls=SafeJSONEncoder)


def test_safe_json_as_dict_key() -> None:
    # A Secret used as a key — pathological but worth catching.
    payload = {Secret("hunter2"): "value"}
    with pytest.raises(TypeError, match="Secret"):
        json.dumps(payload, cls=SafeJSONEncoder)


def test_safe_json_plain_payload_passes_through() -> None:
    assert json.dumps({"x": 1, "y": "ok"}, cls=SafeJSONEncoder) == '{"x": 1, "y": "ok"}'


def test_reveal_returns_plaintext() -> None:
    s = Secret("hunter2")
    assert s.reveal() == "hunter2"


def test_default_json_still_leaks_by_design() -> None:
    """Documents the policy: callers MUST use SafeJSONEncoder for durable sinks.

    Plain ``json.dumps`` would still emit the plaintext because Secret IS a
    str. The platform's API/log/audit emitters wrap every serialisation in
    SafeJSONEncoder; this test exists so a future change doesn't accidentally
    make plain ``json.dumps`` look safe.
    """
    s = Secret("hunter2")
    leaked = json.dumps({"pw": s})
    assert "hunter2" in leaked  # exactly why SafeJSONEncoder exists.
