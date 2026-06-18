"""Secret 브랜드가 repr/str/format/pickle/SafeJSON 어느 경로로도 평문을
드러내지 않음을 검증한다. 누출 벡터마다 한 케이스씩 닫는 보안 회귀 테스트.
"""

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
    # Secret을 dict "키"로 쓴 경우 — 병적이지만 막을 가치가 있는 케이스.
    payload = {Secret("hunter2"): "value"}
    with pytest.raises(TypeError, match="Secret"):
        json.dumps(payload, cls=SafeJSONEncoder)


def test_safe_json_plain_payload_passes_through() -> None:
    assert json.dumps({"x": 1, "y": "ok"}, cls=SafeJSONEncoder) == '{"x": 1, "y": "ok"}'


def test_reveal_returns_plaintext() -> None:
    s = Secret("hunter2")
    assert s.reveal() == "hunter2"


def test_default_json_still_leaks_by_design() -> None:
    """정책을 명문화한다: 영속 싱크에는 호출자가 반드시 SafeJSONEncoder를 써야 한다.

    Secret이 str을 상속하므로 평범한 ``json.dumps``는 여전히 평문을 흘린다.
    플랫폼의 API·로그·감사 emitter는 모든 직렬화를 SafeJSONEncoder로 감싼다.
    이 테스트는 "평범한 json.dumps는 안전하지 않다"는 사실을 의도적으로 고정해,
    훗날 누군가 이 동작을 안전한 것으로 착각해 바꾸지 못하게 하는 가드다.
    """
    s = Secret("hunter2")
    leaked = json.dumps({"pw": s})
    assert "hunter2" in leaked  # SafeJSONEncoder가 존재하는 바로 그 이유.
