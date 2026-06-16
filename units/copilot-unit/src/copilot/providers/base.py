"""CopilotProvider Protocol — providers stream chunks of text.

A provider is anything that accepts a system prompt + chat history and yields
text chunks. The two concrete implementations are
:class:`copilot.providers.anthropic.AnthropicProvider` and
:class:`copilot.providers.ollama.OllamaProvider`.

The Protocol is intentionally narrow so we can add other providers (vLLM,
TGI, sagemaker, etc.) without changing call sites.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str  # "user" or "assistant"
    content: str


class CopilotProvider(Protocol):
    name: str  # short identifier for audit logging

    async def stream(
        self,
        *,
        system: str,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield text chunks as they arrive from the model.

        ``model`` optionally overrides the provider's default model for this
        single call (e.g. a lighter model for one-shot cell edits).
        """
        ...
