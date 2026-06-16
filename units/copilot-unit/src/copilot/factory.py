"""Pick a :class:`CopilotProvider` based on ``LLM_PROVIDER`` env var.

* ``LLM_PROVIDER=anthropic`` → :class:`AnthropicProvider` (requires ``ANTHROPIC_API_KEY``)
* ``LLM_PROVIDER=ollama`` (default for the closed-network demo) →
  :class:`OllamaProvider` (talks to the ``ollama`` compose service)
"""

from __future__ import annotations

import os

from copilot.providers.base import CopilotProvider


def get_provider() -> CopilotProvider:
    name = (os.environ.get("LLM_PROVIDER") or "ollama").lower()
    if name == "anthropic":
        from copilot.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    if name == "ollama":
        from copilot.providers.ollama import OllamaProvider

        return OllamaProvider()
    raise ValueError(f"unknown LLM_PROVIDER: {name!r}")
