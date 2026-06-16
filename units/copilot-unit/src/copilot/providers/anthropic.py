"""Anthropic provider — Claude models via the official SDK.

In closed-network deployments this provider sits behind a sanctioned proxy
(FR-LLM-04). The provider does not inspect or modify request bodies beyond
the system prompt the caller supplies; PII guardrails are enforced upstream
by the prompt builder (metadata-only context) and downstream by response
PII masking in the API router.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from copilot.providers.base import ChatMessage


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        # Import lazily so tests + non-anthropic deployments don't need the SDK.
        from anthropic import AsyncAnthropic

        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self._client = AsyncAnthropic(api_key=api_key)
        # Configurable via COPILOT_ANTHROPIC_MODEL; default is the current
        # valid Sonnet 4.6 model id. An explicit model arg always wins.
        self._model = model or os.environ.get(
            "COPILOT_ANTHROPIC_MODEL", "claude-sonnet-4-6"
        )

    async def stream(
        self,
        *,
        system: str,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        # Use Anthropic prompt caching for the (often large, schema-bearing)
        # system prompt so it's cached server-side across multi-turn requests.
        # Fall back to the plain string when there's nothing worth caching.
        system_param: Any = system
        if system:
            system_param = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        async with self._client.messages.stream(
            model=model or self._model,
            max_tokens=2048,
            temperature=0,
            system=system_param,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        ) as stream:
            async for chunk in stream.text_stream:
                if chunk:
                    yield chunk
