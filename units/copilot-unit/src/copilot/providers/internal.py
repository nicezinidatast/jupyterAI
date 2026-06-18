"""내부망 프로바이더 — Keycloak 게이트웨이 뒤의 온프레미스 vLLM 모델.

폐쇄망 배포에서는 Anthropic 대신 내부 vLLM 클러스터로 코파일럿을 보낼 수
있다. ``INTERNAL_NETWORK``이 truthy일 때 선택된다(:mod:`copilot.factory` 참고).

``INTERNAL_LLM_MODEL``로 두 모델 중 하나를 고른다:

* ``gemma4``     → Gemma-4 31B   (vaiv-gemma4 게이트웨이)
* ``gptoss120b`` → GPT-OSS 120B  (vaiv-gptoss-120b 게이트웨이)

인증은 OpenID *password* grant의 2단계 흐름이다 — 먼저 서비스 계정 자격증명을
Keycloak에 POST 해 수명이 짧은 베어러 토큰(bearer token)을 발급받고, 만료
직전까지 캐시했다가(모듈 레벨 캐시라 팩토리가 요청마다 새로 만드는 프로바이더
인스턴스 사이에서도 재사용됨), 그 토큰으로 모델의 OpenAI 호환
``/v1/chat/completions`` 엔드포인트를 ``stream: true``로 호출해 돌아오는 SSE
(Server-Sent Events) 델타를 중계한다.

모든 엔드포인트·자격증명은 승인된 내부 기본값으로 설정돼 있어
``INTERNAL_NETWORK=True``만 켜면 바로 동작한다. 다른 배포를 위해 모든 값은
여전히 환경 변수로 덮어쓸 수 있다(아래 ``_env`` 호출 참고).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator

import httpx

from copilot.providers.base import ChatMessage

# 내장 모델 레지스트리. 선택 가능한 모델마다 base_url + 페이로드에 넣을
# model id를 둔다. 둘 다 배포별로 INTERNAL_LLM_BASE_URL / INTERNAL_LLM_MODEL_ID
# 환경 변수로 덮어쓸 수 있다.
_MODELS: dict[str, dict[str, str]] = {
    "gemma4": {
        "base_url": "https://vaiv-gemma4.xhub.co.kr/v1/chat/completions",
        "model": "gemma4-31b-vllm",
    },
    "gptoss120b": {
        # 게이트웨이 형태는 같고 서브도메인만 다르다(운영 안내: vaiv-gemma4 →
        # vaiv-gptoss-120b로 교체). 서빙되는 model id는 "-vllm" 컨벤션을 따른다고
        # 가정한 추측값이다 — 클러스터가 다른 id를 보고하면 INTERNAL_LLM_MODEL_ID로
        # 덮어쓸 것.
        "base_url": "https://vaiv-gptoss-120b.xhub.co.kr/v1/chat/completions",
        "model": "gptoss-120b-vllm",
    },
}

# 승인된 내부 기본값. 이 값들 덕분에 INTERNAL_NETWORK=True만으로 충분하다.
_DEFAULT_KEYCLOAK_URL = (
    "https://pass.xhub.co.kr/realms/vllm-prod-apis/protocol/openid-connect/token"
)
_DEFAULT_CLIENT_ID = "vllm-prod-apis-client"
_DEFAULT_CLIENT_SECRET = "GQe3XyBPZDMzXSTRpaAbv5tHdjee3q9o"
_DEFAULT_USERNAME = "hgkim"
_DEFAULT_PASSWORD = "User1234!!"

# 모듈 레벨 토큰 캐시. 팩토리가 요청마다 프로바이더를 새로 만들기 때문에,
# 캐시가 인스턴스가 아니라 여기(모듈)에 있어야 실제로 재사용된다. 키는
# (keycloak_url, client_id, username) → (access_token, monotonic 만료시각).
_token_cache: dict[tuple[str, str, str], tuple[str, float]] = {}
_token_lock = asyncio.Lock()


def _env(name: str, default: str) -> str:
    """os.environ.get과 같되, 빈 문자열을 미설정과 동일하게 취급한다."""
    v = os.environ.get(name)
    return v if v else default


class InternalVLLMProvider:
    def __init__(self, *, model: str | None = None) -> None:
        key = (model or os.environ.get("INTERNAL_LLM_MODEL") or "gemma4").lower()
        if key not in _MODELS:
            raise ValueError(
                f"unknown INTERNAL_LLM_MODEL: {key!r} "
                f"(expected one of {sorted(_MODELS)})"
            )
        self._model_key = key
        # name에 모델명을 실어 두면, SPA(단일 페이지 앱)의 배지와 감사 로그 행에
        # 어느 내부 모델이 답했는지 드러난다(예: "internal/gemma4").
        self.name = f"internal/{key}"

        self._base_url = _env("INTERNAL_LLM_BASE_URL", _MODELS[key]["base_url"])
        self._model = _env("INTERNAL_LLM_MODEL_ID", _MODELS[key]["model"])

        self._keycloak_url = _env("INTERNAL_KEYCLOAK_URL", _DEFAULT_KEYCLOAK_URL)
        self._client_id = _env("INTERNAL_KEYCLOAK_CLIENT_ID", _DEFAULT_CLIENT_ID)
        self._client_secret = _env(
            "INTERNAL_KEYCLOAK_CLIENT_SECRET", _DEFAULT_CLIENT_SECRET
        )
        self._username = _env("INTERNAL_LLM_USERNAME", _DEFAULT_USERNAME)
        self._password = _env("INTERNAL_LLM_PASSWORD", _DEFAULT_PASSWORD)

        # 폐쇄망에서는 자체 서명 인증서(self-signed cert)가 흔하다 — 인증서 검증을
        # 끌 수 있게 한다(기본은 켜짐). INTERNAL_LLM_VERIFY_SSL=false면 건너뛴다.
        self._verify = os.environ.get(
            "INTERNAL_LLM_VERIFY_SSL", "true"
        ).strip().lower() not in ("0", "false", "no", "off")
        # vLLM 콜드 스타트나 긴 생성은 느릴 수 있으므로 읽기 타임아웃을 넉넉히 준다.
        self._timeout = httpx.Timeout(120.0, connect=10.0)

    async def _get_token(self) -> str:
        """캐시된 베어러 토큰을 돌려주거나, 없으면 Keycloak에서 새로 발급받는다.

        이중 검사 잠금(double-checked locking) 패턴이다 — 락 밖에서 한 번 빠르게
        확인하고(흔한 경로), 캐시가 비었으면 락을 잡은 뒤 다시 확인한다. 동시에
        들어온 요청 무리가 토큰을 각각 발급받지 않고 단 한 번만 발급하게 만든다.
        """
        cache_key = (self._keycloak_url, self._client_id, self._username)
        now = time.monotonic()
        cached = _token_cache.get(cache_key)
        if cached is not None and now < cached[1]:
            return cached[0]
        # 동시 갱신을 직렬화해, 요청이 몰려도 토큰은 한 번만 발급되게 한다.
        async with _token_lock:
            # 락을 기다리는 동안 다른 코루틴이 이미 갱신했을 수 있으니 다시 확인.
            now = time.monotonic()
            cached = _token_cache.get(cache_key)
            if cached is not None and now < cached[1]:
                return cached[0]
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(15.0, connect=10.0), verify=self._verify
            ) as client:
                resp = await client.post(
                    self._keycloak_url,
                    data={
                        "grant_type": "password",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "username": self._username,
                        "password": self._password,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                resp.raise_for_status()
                body = resp.json()
            token = body["access_token"]
            # 서버가 알려준 만료보다 ~30초 앞당겨 갱신한다(기본 5분). 만료 직전
            # 토큰으로 호출하다 도중에 무효화되는 일을 막기 위한 안전 여유.
            # 다만 expires_in이 비정상적으로 짧아도 최소 30초는 캐시한다.
            expires_in = float(body.get("expires_in", 300))
            _token_cache[cache_key] = (
                token,
                time.monotonic() + max(expires_in - 30.0, 30.0),
            )
            return token

    async def stream(
        self,
        *,
        system: str,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        # 주의: 호출별 ``model`` 덮어쓰기를 여기서는 일부러 무시한다. 이 인자를
        # 넘기는 유일한 호출자(edit-cell)는 COPILOT_EDIT_MODEL을 넘기는데, 그건
        # Anthropic 모델 id다 — 그걸 vLLM에 넣으면 404가 난다. 내부 게이트웨이는
        # 각각 정확히 한 모델만 서빙하므로 항상 self._model을 쓴다.
        token = await self._get_token()
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}]
            + [{"role": m["role"], "content": m["content"]} for m in messages],
            "stream": True,
            "temperature": 0,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        async with httpx.AsyncClient(timeout=self._timeout, verify=self._verify) as client:
            async with client.stream(
                "POST", self._base_url, headers=headers, json=payload
            ) as resp:
                resp.raise_for_status()
                # OpenAI 호환 SSE 형식: ``data: {json}`` 모양의 줄들이 이어지다가
                # 마지막에 ``data: [DONE]``으로 끝난다. data: 접두가 없는 줄(빈 줄·
                # 주석·keep-alive)은 건너뛴다.
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        return
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    # 델타에 content가 없는 청크(역할만 알리는 첫 델타 등)도 있어
                    # 방어적으로 꺼낸 뒤 비어 있으면 흘려보낸다.
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    chunk = (choices[0].get("delta") or {}).get("content")
                    if chunk:
                        yield chunk
