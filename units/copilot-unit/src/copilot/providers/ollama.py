"""Ollama 프로바이더 — 로컬 LLM. 폐쇄망(closed-network) 배포에 딱 맞는다.

Ollama의 ``/api/chat``가 돌려주는 줄 단위 JSON(newline-delimited JSON)을
받아 스트리밍한다. HTTP 타임아웃을 일부러 길게 잡는데, 7B 모델은
콜드 스타트(cold-start)에 10~30초가 걸릴 수 있기 때문이다.
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
                # 응답은 한 줄에 JSON 한 개. 빈 줄이나 깨진 줄은 건너뛰어
                # (방어적 파싱) 부분 수신·keep-alive 줄에도 견디게 한다.
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
                    # done=true는 스트림 종료 신호. 받는 즉시 빠져나간다.
                    if obj.get("done"):
                        return
