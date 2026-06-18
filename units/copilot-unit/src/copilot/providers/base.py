"""CopilotProvider 프로토콜 — 프로바이더는 텍스트 청크를 스트리밍한다.

프로바이더(provider)란 시스템 프롬프트 + 대화 이력을 받아 텍스트 청크를
yield 하는 모든 구현을 가리킨다. 구체 구현은 세 가지로,
:class:`copilot.providers.anthropic.AnthropicProvider`,
:class:`copilot.providers.ollama.OllamaProvider`,
:class:`copilot.providers.internal.InternalVLLMProvider`(내부망 vLLM)이다.

프로토콜을 일부러 좁게 잡은 이유: 호출부(call site)를 건드리지 않고도
다른 프로바이더(vLLM, TGI, sagemaker 등)를 추가할 수 있게 하기 위함이다.
즉 모든 프로바이더는 동일한 `stream` 계약만 만족하면 되고, 팩토리
(:mod:`copilot.factory`)가 환경에 맞는 구현을 골라 준다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str  # "user" 또는 "assistant"
    content: str


class CopilotProvider(Protocol):
    name: str  # 감사 로그(audit log)에 남길 짧은 식별자

    async def stream(
        self,
        *,
        system: str,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """모델에서 도착하는 대로 텍스트 청크를 yield 한다.

        ``model``은 이번 한 번의 호출에 한해 프로바이더의 기본 모델을 덮어쓰는
        선택 인자다(예: 한 번에 끝나는 셀 편집에는 더 가벼운 모델을 쓰는 식).
        """
        ...
