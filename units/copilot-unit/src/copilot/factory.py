"""환경 변수를 보고 :class:`CopilotProvider` 구현을 하나 고른다.

선택 순서(resolution order):

1. ``INTERNAL_NETWORK``이 truthy(``true``/``1``/``yes``/``on``)이면 →
   :class:`InternalVLLMProvider` — Keycloak 뒤의 온프레미스 vLLM. 구체 모델은
   ``INTERNAL_LLM_MODEL``(``gemma4`` | ``gptoss120b``)로 정한다.
2. 그렇지 않으면 ``LLM_PROVIDER``로 폴백:
   * ``anthropic`` → :class:`AnthropicProvider` (``ANTHROPIC_API_KEY`` 필요)
   * ``ollama`` (폐쇄망 데모의 기본값) → :class:`OllamaProvider`
   * ``internal`` → :class:`InternalVLLMProvider` (``INTERNAL_NETWORK`` 플래그
     없이 명시적으로 내부망 vLLM을 골라 쓰는 경로)

따라서 온프레미스 전환은 ``backend/.env``의 ``INTERNAL_NETWORK=True`` 한 줄로
끝난다. 이 값을 끄면 모든 동작이 예전 그대로 돌아간다.

프로바이더 import는 함수 안에서 지연(lazy)으로 한다. 안 쓰는 프로바이더의
SDK(예: anthropic)나 무거운 의존성을 배포·테스트 환경에서 강제로 들이지
않기 위함이다.
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
    """:func:`get_provider`가 돌려줄 프로바이더를, 네트워크 호출 없이 요약한다.

    백엔드 기동 로그(``docker logs``에서 어떤 모델이 답할지 보이도록)와
    ``python -m copilot.selftest``가 쓴다. 프로바이더를 생성만 하고 네트워크
    호출은 하지 않는다. ``get_provider``와 똑같은 오류를 그대로 던진다(예:
    ANTHROPIC_API_KEY 미설정, 알 수 없는 INTERNAL_LLM_MODEL).

    ``_model`` / ``_base_url``은 프로토콜에 없는 내부 속성이라
    :func:`getattr`로 안전하게 꺼낸다(프로바이더마다 있을 수도, 없을 수도 있음).
    """
    p = get_provider()
    return {
        "provider": p.name,
        "model": getattr(p, "_model", None),
        "endpoint": getattr(p, "_base_url", None),
        "internal_network": os.environ.get("INTERNAL_NETWORK") or "false",
    }
