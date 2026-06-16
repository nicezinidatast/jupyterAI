"""factory.get_provider — env-driven dispatch."""

from __future__ import annotations

import os

import pytest

from copilot.factory import get_provider


def test_default_is_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
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
    monkeypatch.setenv("LLM_PROVIDER", "totally-bogus")
    with pytest.raises(ValueError, match="totally-bogus"):
        get_provider()
