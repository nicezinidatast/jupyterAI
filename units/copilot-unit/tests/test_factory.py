"""factory.get_provider — env-driven dispatch."""

from __future__ import annotations

import os

import pytest

from copilot.factory import get_provider


def test_default_is_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("INTERNAL_NETWORK", raising=False)
    p = get_provider()
    assert p.name == "ollama"


def test_anthropic_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_provider()


def test_anthropic_constructs_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-DUMMY")
    p = get_provider()
    assert p.name == "anthropic"


def test_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTERNAL_NETWORK", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "totally-bogus")
    with pytest.raises(ValueError, match="totally-bogus"):
        get_provider()


def test_internal_network_overrides_llm_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # INTERNAL_NETWORK wins even when LLM_PROVIDER says anthropic.
    monkeypatch.setenv("INTERNAL_NETWORK", "True")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("INTERNAL_LLM_MODEL", raising=False)
    p = get_provider()
    assert p.name == "internal/gemma4"  # gemma4 is the default model


def test_internal_network_falsey_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_NETWORK", "False")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    p = get_provider()
    assert p.name == "ollama"


def test_internal_model_selection_gptoss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_NETWORK", "1")
    monkeypatch.setenv("INTERNAL_LLM_MODEL", "gptoss120b")
    p = get_provider()
    assert p.name == "internal/gptoss120b"


def test_internal_unknown_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_NETWORK", "yes")
    monkeypatch.setenv("INTERNAL_LLM_MODEL", "bogus-model")
    with pytest.raises(ValueError, match="bogus-model"):
        get_provider()
