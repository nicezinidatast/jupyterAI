"""Internal-network provider — on-prem vLLM models behind a Keycloak gateway.

Closed-network deployments can route the copilot at an internal vLLM cluster
instead of Anthropic. Selected when ``INTERNAL_NETWORK`` is truthy (see
:mod:`copilot.factory`).

Two models are exposed, picked via ``INTERNAL_LLM_MODEL``:

* ``gemma4``     → Gemma-4 31B   (vaiv-gemma4 gateway)
* ``gptoss120b`` → GPT-OSS 120B  (vaiv-gptoss-120b gateway)

Auth is a two-step OpenID *password* grant: we POST service credentials to
Keycloak to mint a short-lived bearer token, cache it (module-level, so it is
reused across the per-request provider instances the factory hands out) until
just before it expires, then call the model's OpenAI-compatible
``/v1/chat/completions`` endpoint with ``stream: true`` and relay the SSE
deltas.

All endpoints/credentials default to the sanctioned internal values so that
simply setting ``INTERNAL_NETWORK=True`` works out of the box; every value is
still overridable via env for other deployments (see the ``_env`` calls).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator

import httpx

from copilot.providers.base import ChatMessage

# Built-in model registry. base_url + payload model id per selectable model.
# Both are overridable per-deploy via INTERNAL_LLM_BASE_URL / INTERNAL_LLM_MODEL_ID.
_MODELS: dict[str, dict[str, str]] = {
    "gemma4": {
        "base_url": "https://vaiv-gemma4.xhub.co.kr/v1/chat/completions",
        "model": "gemma4-31b-vllm",
    },
    "gptoss120b": {
        # Same gateway shape, different subdomain (per ops: swap vaiv-gemma4 →
        # vaiv-gptoss-120b). The served model id follows the "-vllm" convention;
        # override with INTERNAL_LLM_MODEL_ID if the cluster reports otherwise.
        "base_url": "https://vaiv-gptoss-120b.xhub.co.kr/v1/chat/completions",
        "model": "gptoss-120b-vllm",
    },
}

# Sanctioned internal defaults so INTERNAL_NETWORK=True alone is enough.
_DEFAULT_KEYCLOAK_URL = (
    "https://pass.xhub.co.kr/realms/vllm-prod-apis/protocol/openid-connect/token"
)
_DEFAULT_CLIENT_ID = "vllm-prod-apis-client"
_DEFAULT_CLIENT_SECRET = "GQe3XyBPZDMzXSTRpaAbv5tHdjee3q9o"
_DEFAULT_USERNAME = "hgkim"
_DEFAULT_PASSWORD = "User1234!!"

# Module-level token cache. The factory builds a fresh provider per request, so
# the cache must live here (not on the instance) to actually be reused. Keyed by
# (keycloak_url, client_id, username) → (access_token, monotonic_expiry).
_token_cache: dict[tuple[str, str, str], tuple[str, float]] = {}
_token_lock = asyncio.Lock()


def _env(name: str, default: str) -> str:
    """os.environ.get, but treats empty string the same as unset."""
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
        # Audit/label name carries the model so the SPA badge + audit rows show
        # which internal model answered (e.g. "internal/gemma4").
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

        # Self-signed certs are common on closed networks — allow opting out of
        # verification (default on). Set INTERNAL_LLM_VERIFY_SSL=false to skip.
        self._verify = os.environ.get(
            "INTERNAL_LLM_VERIFY_SSL", "true"
        ).strip().lower() not in ("0", "false", "no", "off")
        # vLLM cold-start / long generations can be slow; generous read timeout.
        self._timeout = httpx.Timeout(120.0, connect=10.0)

    async def _get_token(self) -> str:
        cache_key = (self._keycloak_url, self._client_id, self._username)
        now = time.monotonic()
        cached = _token_cache.get(cache_key)
        if cached is not None and now < cached[1]:
            return cached[0]
        # Serialize concurrent refreshes so a burst of requests mints one token.
        async with _token_lock:
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
            # Refresh ~30s before the server-stated expiry (default 5 min).
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
        # NOTE: the per-call ``model`` override is intentionally ignored here.
        # The only caller that sets it (edit-cell) passes COPILOT_EDIT_MODEL,
        # which is an Anthropic model id — feeding that to vLLM would 404. Each
        # internal gateway serves exactly one model, so we always use self._model.
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
                # OpenAI-compatible SSE: lines like ``data: {json}`` ending with
                # ``data: [DONE]``.
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
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    chunk = (choices[0].get("delta") or {}).get("content")
                    if chunk:
                        yield chunk
