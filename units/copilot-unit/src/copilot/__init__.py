"""copilot-unit — natural-language assistant for analysts.

Public surface:

* :func:`copilot.factory.get_provider` — returns the configured ``CopilotProvider``
  (Anthropic or Ollama) based on the ``LLM_PROVIDER`` env var.
* :mod:`copilot.prompts` — builds system prompts that inject schema context
  (metadata only — never row data; see FR-LLM-05).
* :mod:`copilot.providers.base` — ``CopilotProvider`` Protocol + ``ChatMessage``
  TypedDict.

The unit exposes a FastAPI router at :mod:`copilot.api.router`.
"""
