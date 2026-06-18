"""Anthropic 프로바이더 — 공식 SDK로 Claude 모델을 호출한다.

폐쇄망 배포에서는 이 프로바이더가 승인된 프록시(sanctioned proxy) 뒤에
위치한다(FR-LLM-04). 호출자가 넘긴 시스템 프롬프트 외에 요청 본문을
들여다보거나 손대지 않는다. PII(개인식별정보) 가드레일은 양쪽 끝에서
강제된다 — 상류(upstream)에서는 프롬프트 빌더가 메타데이터만 담고,
하류(downstream)에서는 API 라우터가 응답을 PII 마스킹한다.
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
        # SDK는 함수 안에서 지연 import 한다. 테스트나 anthropic을 안 쓰는
        # 배포가 SDK 설치를 강제당하지 않게 하기 위함이다.
        from anthropic import AsyncAnthropic

        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self._client = AsyncAnthropic(api_key=api_key)
        # COPILOT_ANTHROPIC_MODEL로 바꿀 수 있고, 기본값은 현재 유효한
        # Sonnet 4.6 모델 id다. 인자로 넘긴 model이 있으면 그게 항상 우선한다.
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
        # 시스템 프롬프트는 보통 크고 스키마를 담고 있어 멀티턴(multi-turn)
        # 요청에서 매번 재전송하면 낭비다. Anthropic 프롬프트 캐싱
        # (prompt caching)으로 서버 쪽에 캐시해 두고 재사용한다. 캐싱할
        # 가치가 없으면(빈 system) 평범한 문자열로 폴백한다.
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
