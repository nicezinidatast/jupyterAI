"""InternalVLLMProvider — offline token + SSE streaming, no real network.

We monkeypatch ``httpx.AsyncClient`` to inject a ``MockTransport`` so both the
Keycloak token POST and the OpenAI-compatible streaming call are served from a
handler. This verifies the real two-step flow (mint token → stream deltas)
without touching the internal network.
"""

from __future__ import annotations

import json

import httpx
import pytest

import copilot.providers.internal as internal
from copilot.providers.internal import InternalVLLMProvider


def _install_mock(monkeypatch: pytest.MonkeyPatch, handler) -> dict:
    """Route every httpx.AsyncClient through MockTransport(handler).

    Returns a dict the handler can mutate to record what it saw.
    """
    seen: dict = {"token_calls": 0, "chat_payloads": []}
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(lambda req: handler(req, seen))
        return real(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return seen


def _default_handler(req: httpx.Request, seen: dict) -> httpx.Response:
    if "openid-connect/token" in str(req.url):
        seen["token_calls"] += 1
        return httpx.Response(
            200, json={"access_token": "tok-abc", "expires_in": 300}
        )
    # chat/completions — assert bearer + capture payload, return SSE deltas.
    assert req.headers.get("Authorization") == "Bearer tok-abc"
    seen["chat_payloads"].append(json.loads(req.content))
    body = (
        'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":", world"}}]}\n\n'
        'data: {"choices":[{"delta":{}}]}\n\n'
        "data: [DONE]\n\n"
    )
    return httpx.Response(200, content=body.encode("utf-8"))


async def _collect(provider: InternalVLLMProvider) -> str:
    out = []
    async for chunk in provider.stream(
        system="be terse", messages=[{"role": "user", "content": "hi"}]
    ):
        out.append(chunk)
    return "".join(out)


@pytest.mark.asyncio
async def test_stream_mints_token_then_relays_deltas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    internal._token_cache.clear()
    monkeypatch.setenv("INTERNAL_LLM_MODEL", "gemma4")
    seen = _install_mock(monkeypatch, _default_handler)

    provider = InternalVLLMProvider()
    text = await _collect(provider)

    assert text == "Hello, world"
    assert seen["token_calls"] == 1
    # gemma4 → correct model id + streaming flag in the request body.
    assert seen["chat_payloads"][0]["model"] == "gemma4-31b-vllm"
    assert seen["chat_payloads"][0]["stream"] is True
    # system prompt is sent as the leading system message.
    assert seen["chat_payloads"][0]["messages"][0] == {
        "role": "system",
        "content": "be terse",
    }


@pytest.mark.asyncio
async def test_token_cached_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    internal._token_cache.clear()
    monkeypatch.setenv("INTERNAL_LLM_MODEL", "gemma4")
    seen = _install_mock(monkeypatch, _default_handler)

    # Two separate provider instances (mirrors the per-request factory) must
    # share one minted token.
    await _collect(InternalVLLMProvider())
    await _collect(InternalVLLMProvider())

    assert seen["token_calls"] == 1
    assert len(seen["chat_payloads"]) == 2


@pytest.mark.asyncio
async def test_gptoss_uses_its_own_model_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    internal._token_cache.clear()
    monkeypatch.setenv("INTERNAL_LLM_MODEL", "gptoss120b")
    seen = _install_mock(monkeypatch, _default_handler)

    await _collect(InternalVLLMProvider())

    assert seen["chat_payloads"][0]["model"] == "gptoss-120b-vllm"


@pytest.mark.asyncio
async def test_edit_model_override_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # edit-cell passes COPILOT_EDIT_MODEL (a Claude id) as model=; the internal
    # provider must NOT forward it to vLLM.
    internal._token_cache.clear()
    monkeypatch.setenv("INTERNAL_LLM_MODEL", "gemma4")
    seen = _install_mock(monkeypatch, _default_handler)

    provider = InternalVLLMProvider()
    out = []
    async for chunk in provider.stream(
        system="x",
        messages=[{"role": "user", "content": "y"}],
        model="claude-haiku-4-5-20251001",
    ):
        out.append(chunk)

    assert seen["chat_payloads"][0]["model"] == "gemma4-31b-vllm"
