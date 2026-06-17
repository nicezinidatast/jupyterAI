"""Pick a :class:`CopilotProvider`.

Resolution order:

1. ``INTERNAL_NETWORK`` truthy (``true``/``1``/``yes``/``on``) →
   :class:`InternalVLLMProvider` — on-prem vLLM behind Keycloak. The specific
   model comes from ``INTERNAL_LLM_MODEL`` (``gemma4`` | ``gptoss120b``).
2. Otherwise fall back to ``LLM_PROVIDER``:
   * ``anthropic`` → :class:`AnthropicProvider` (requires ``ANTHROPIC_API_KEY``)
   * ``ollama`` (default for the closed-network demo) → :class:`OllamaProvider`
   * ``internal`` → :class:`InternalVLLMProvider` (explicit opt-in without the
     ``INTERNAL_NETWORK`` flag)

So the on-prem toggle is a single ``INTERNAL_NETWORK=True`` in ``backend/.env``;
flip it off and everything behaves exactly as before.
"""

from __future__ import annotations

import os

from copilot.providers.base import CopilotProvider

_TRUTHY = frozenset({"true", "1", "yes", "on"})


def _internal_network_enabled() -> bool:
    return (os.environ.get("INTERNAL_NETWORK") or "").strip().lower() in _TRUTHY


def get_provider() -> CopilotProvider:
    if _internal_network_enabled():
        from copilot.providers.internal import InternalVLLMProvider

        return InternalVLLMProvider()

    name = (os.environ.get("LLM_PROVIDER") or "ollama").lower()
    if name == "anthropic":
        from copilot.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    if name == "ollama":
        from copilot.providers.ollama import OllamaProvider

        return OllamaProvider()
    if name == "internal":
        from copilot.providers.internal import InternalVLLMProvider

        return InternalVLLMProvider()
    raise ValueError(f"unknown LLM_PROVIDER: {name!r}")


def describe_active() -> dict[str, str | None]:
    """Non-network summary of the provider :func:`get_provider` would return.

    Used by the backend startup log (so ``docker logs`` shows which model will
    answer) and by ``python -m copilot.selftest``. Constructs the provider but
    makes no network call; raises the same errors ``get_provider`` would (e.g.
    missing ANTHROPIC_API_KEY, unknown INTERNAL_LLM_MODEL).
    """
    p = get_provider()
    return {
        "provider": p.name,
        "model": getattr(p, "_model", None),
        "endpoint": getattr(p, "_base_url", None),
        "internal_network": os.environ.get("INTERNAL_NETWORK") or "false",
    }
