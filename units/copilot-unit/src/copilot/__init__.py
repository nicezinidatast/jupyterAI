"""copilot-unit — 분석가를 위한 자연어 어시스턴트.

공개 표면(public surface):

* :func:`copilot.factory.get_provider` — 설정된 ``CopilotProvider``를 돌려준다.
  ``INTERNAL_NETWORK=True``이면 온프레미스 vLLM 프로바이더를 고른다(Keycloak으로
  게이트되는 Gemma-4 / GPT-OSS-120B, ``INTERNAL_LLM_MODEL``로 선택). 그렇지
  않으면 ``LLM_PROVIDER`` 환경 변수가 Anthropic 또는 Ollama를 고른다.
* :mod:`copilot.prompts` — 스키마 맥락을 주입한 시스템 프롬프트를 만든다
  (메타데이터만 — 행 데이터는 절대 미포함; FR-LLM-05 참고).
* :mod:`copilot.providers.base` — ``CopilotProvider`` 프로토콜과 ``ChatMessage``
  TypedDict.

이 유닛은 :mod:`copilot.api.router`에 FastAPI 라우터를 노출한다.
"""
