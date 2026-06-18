"""코파일럿 1회용 자가 점검(self-test) — 설정된 LLM이 실제로 답하는지 확인한다.

백엔드 컨테이너(``copilot`` 패키지와 앱이 쓰는 동일한 환경을 갖춘) 안에서
실행한다::

    docker compose -f infra/docker-compose/compose.yml exec backend \
        python -m copilot.selftest

해석된 프로바이더/모델/엔드포인트를 출력하고, 고정된 한국어 프롬프트로 스트리밍
왕복(round-trip)을 한 번 날려 답을 흘려 보여 준 뒤, 어떤 실패든 0이 아닌 종료
코드로 끝낸다 — 그래서 내부망에서의 연결성/자격증명/model-id 스모크 점검
(smoke check)을 겸한다.
"""

from __future__ import annotations

import asyncio
import os
import sys

from copilot.factory import describe_active, get_provider

_PROMPT = "안녕하세요, 너는 어떤 LLM이니? 한 문장으로 답해줘."


async def _run() -> int:
    # Windows 콘솔에서 한국어 출력이 깨지지 않게 UTF-8로 재설정한다(리눅스
    # 컨테이너에서는 사실상 무의미한 동작이지만, 실패해도 그냥 넘어간다).
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
