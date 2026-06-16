"""Ollama provider — local LLM, perfect fit for closed-network deployments.

Streams via Ollama's ``/api/chat`` newline-delimited JSON response. The
HTTP timeout is intentionally long because cold-start on a 7B model can
take 10–30 seconds.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

import httpx

from copilot.providers.base import ChatMessage


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")).rstrip("/")
        self._model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self._timeout = httpx.Timeout(60.0, connect=10.0)

    async def stream(
        self,
        *,
        system: str,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model or self._model,
            "messages": [{"role": "system", "content": system}]
            + [{"role": m["role"], "content": m["content"]} for m in messages],
            "stream": True,
            "options": {"temperature": 0.1, "num_predict": 1024},
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    chunk = (obj.get("message") or {}).get("content")
                    if chunk:
                        yield chunk
                    if obj.get("done"):
                        return
