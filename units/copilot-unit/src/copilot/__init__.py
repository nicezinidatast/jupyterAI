"""copilot-unit — natural-language assistant for analysts.

Public surface:

* :func:`copilot.factory.get_provider` — returns the configured ``CopilotProvider``.
  ``INTERNAL_NETWORK=True`` selects the on-prem vLLM provider (Keycloak-gated
  Gemma-4 / GPT-OSS-120B, chosen via ``INTERNAL_LLM_MODEL``); otherwise the
  ``LLM_PROVIDER`` env var picks Anthropic or Ollama.
* :mod:`copilot.prompts` — builds system prompts that inject schema context
  (metadata only — never row data; see FR-LLM-05).
* :mod:`copilot.providers.base` — ``CopilotProvider`` Protocol + ``ChatMessage``
  TypedDict.

The unit exposes a FastAPI router at :mod:`copilot.api.router`.
"""
