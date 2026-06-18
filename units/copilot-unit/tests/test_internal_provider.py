"""InternalVLLMProvider 테스트 — 오프라인 토큰 + SSE 스트리밍, 실제 네트워크 없음.

``httpx.AsyncClient``를 몽키패치해 ``MockTransport``를 주입한다. 그러면
Keycloak 토큰 POST와 OpenAI 호환 스트리밍 호출이 모두 하나의 핸들러에서
응답된다. 내부망을 건드리지 않고도 실제 2단계 흐름(토큰 발급 → 델타 스트리밍)을
검증할 수 있다.
"""

from __future__ import annotations

import json

import httpx
import pytest

import copilot.providers.internal as internal
from copilot.providers.internal import InternalVLLMProvider


def _install_mock(monkeypatch: pytest.MonkeyPatch, handler) -> dict:
    """모든 httpx.AsyncClient를 MockTransport(handler)로 통과시키게 만든다.

    핸들러가 본 것을 기록할 수 있도록, 변경 가능한 dict를 돌려준다.
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
    # chat/completions — 베어러 토큰 확인 + 페이로드 캡처, SSE 델타 반환.
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
    # gemma4 → 요청 본문에 올바른 model id와 스트리밍 플래그가 실린다.
    assert seen["chat_payloads"][0]["model"] == "gemma4-31b-vllm"
    assert seen["chat_payloads"][0]["stream"] is True
    # 시스템 프롬프트는 맨 앞 system 메시지로 전송된다.
    assert seen["chat_payloads"][0]["messages"][0] == {
        "role": "system",
        "content": "be terse",
    }


@pytest.mark.asyncio
async def test_token_cached_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    internal._token_cache.clear()
    monkeypatch.setenv("INTERNAL_LLM_MODEL", "gemma4")
    seen = _install_mock(monkeypatch, _default_handler)

    # 서로 다른 프로바이더 인스턴스 두 개(요청마다 새로 만드는 팩토리를 모사)가
    # 발급된 토큰 하나를 공유해야 한다.
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
    # edit-cell은 COPILOT_EDIT_MODEL(Claude id)을 model=로 넘긴다. 내부망
    # 프로바이더는 그걸 vLLM으로 전달하면 안 된다(자기 모델 id를 써야 함).
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
