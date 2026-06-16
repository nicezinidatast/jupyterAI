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

from copilot.providers.base import ChatMessage


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
    ) -> None:
        # Import lazily so tests + non-anthropic deployments don't need the SDK.
        from anthropic import AsyncAnthropic

        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def stream(
        self,
        *,
        system: str,
        messages: list[ChatMessage],
    ) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=2048,
            system=system,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        ) as stream:
            async for chunk in stream.text_stream:
                if chunk:
                    yield chunk
