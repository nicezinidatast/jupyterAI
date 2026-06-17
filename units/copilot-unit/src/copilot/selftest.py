"""One-shot copilot self-test — confirm the configured LLM actually answers.

Run it inside the backend container (which has the ``copilot`` package + the
same env the app uses)::

    docker compose -f infra/docker-compose/compose.yml exec backend \
        python -m copilot.selftest

It prints the resolved provider/model/endpoint, fires a single streaming
round-trip with a fixed Korean prompt, streams the answer, and exits non-zero
on any failure — so it doubles as a connectivity / credential / model-id smoke
check on the internal network.
"""

from __future__ import annotations

import asyncio
import os
import sys

from copilot.factory import describe_active, get_provider

_PROMPT = "안녕하세요, 너는 어떤 LLM이니? 한 문장으로 답해줘."


async def _run() -> int:
    # Korean output safety on Windows consoles (no-op in the linux container).
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass

    try:
        info = describe_active()
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] provider 생성 실패: {e}")
        return 1

    print(f"INTERNAL_NETWORK = {os.environ.get('INTERNAL_NETWORK', '(unset)')}")
    print(f"provider         = {info['provider']}")
    print(f"model            = {info['model']}")
    if info["endpoint"]:
        print(f"endpoint         = {info['endpoint']}")
    print("-" * 64)
    print(f"질문: {_PROMPT}")
    print("응답: ", end="", flush=True)

    provider = get_provider()
    chars = 0
    try:
        async for chunk in provider.stream(
            system="항상 한국어로만 답변해 줘.",
            messages=[{"role": "user", "content": _PROMPT}],
        ):
            sys.stdout.write(chunk)
            sys.stdout.flush()
            chars += len(chunk)
    except Exception as e:  # noqa: BLE001
        print(f"\n[FAIL] LLM 호출 실패: {e}")
        return 1

    print("\n" + "-" * 64)
    if chars == 0:
        print("[FAIL] 응답이 비어 있습니다 (0 chars 수신).")
        return 1
    print(f"[OK] 정상 — {chars} 글자 수신, provider={info['provider']}")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
