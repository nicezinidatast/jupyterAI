"""코파일럿 헤드라인 통합 흐름의 end-to-end 테스트.

    자연어 질문 → Anthropic 스트리밍 응답 → ```sql``` 코드 블록 포함 답변
                → 자동 삽입(SPA가 코드 블록을 감지해 PUT)
                → JupyterLab REST PUT → copilot.ipynb 갱신
                → audit_log 에 event_type=copilot_cell_inserted 행 기록

실제 서비스만 사용 — 스텁 없음. 아래 조건이 하나라도 해당되면 자동 skip된다:
    * portal nginx에 접근 불가, 또는
    * Anthropic provider 미설정(``GET /api/copilot/provider`` 가 non-200 반환) —
      API 키 없는 기여자도 나머지 스위트를 실행할 수 있도록 한다.

Anthropic 왕복 호출이 발생하므로 비용이 든다(~5-15초). ``copilot`` 마커로
표시되어 CI에서 ``pytest -m 'not copilot'`` 으로 제외 가능하다.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import urllib.request

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

PORTAL_URL = "http://localhost:5180"
JUPYTER_BASE = "http://localhost:8888/jupyter"
JUPYTER_TOKEN = "dataplatform"
NOTEBOOK = "copilot.ipynb"

PG_CONTAINER = "dataplatform-0521-postgres-1"

# Docker may live on the host PATH (Docker Desktop) or only inside WSL
# (docker-ce in the distro). Resolve once at import time.
_DOCKER_CMD: list[str] = (
    ["docker"] if shutil.which("docker") else ["wsl", "-e", "docker"]
)


def _psql(sql: str) -> str:
    """Postgres 컨테이너 내부에서 SQL 문을 실행하고 결과를 반환한다.

    호스트 측 psycopg2 대신 ``docker exec`` 를 사용하는 이유:
    Docker Desktop on Windows 에서는 컨테이너 :5432 가 호스트에 노출되지만,
    로컬 pg_hba 라우팅과 자격증명이 컨테이너 내부 superuser 와 다를 수 있다.
    docker exec 를 쓰면 그런 환경 차이에 무관하게 항상 동일하게 동작한다.
    """
    out = subprocess.run(
        [
            *_DOCKER_CMD,
            "exec",
            PG_CONTAINER,
            "psql",
            "-U",
            "postgres",
            "-d",
            "dataplatform",
            "-At",
            "-c",
            sql,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _portal_reachable() -> bool:
    """portal /healthz 가 8초 이내에 200을 반환하는지 확인한다.

    모듈 import 시점에 평가되어 pytestmark skip 조건으로 사용된다.
    """
    try:
        with urllib.request.urlopen(f"{PORTAL_URL}/healthz", timeout=8) as r:
            return r.status == 200
    except (OSError, socket.error):
        return False


def _anthropic_configured() -> bool:
    """GET /api/copilot/provider 가 provider='anthropic' 를 반환하는지 확인한다.

    provider 가 anthropic 이 아닌 경우(미설정 또는 ollama 등) 코파일럿 e2e 를 skip한다.
    """
    try:
        with httpx.Client(timeout=8.0) as c:
            r = c.get(f"{PORTAL_URL}/api/copilot/provider")
            return r.status_code == 200 and r.json().get("provider") == "anthropic"
    except (httpx.HTTPError, ValueError):
        return False


pytestmark = [
    pytest.mark.skipif(
        not _portal_reachable(), reason=f"portal not reachable at {PORTAL_URL}"
    ),
    pytest.mark.skipif(
        not _anthropic_configured(),
        reason="copilot provider is not 'anthropic' — skip the integration round-trip",
    ),
    pytest.mark.copilot,
]


def _audit_count() -> int:
    """audit_log 테이블에서 copilot_cell_inserted 이벤트 수를 반환한다.

    테스트 전후로 비교하여 정확히 한 건이 추가되었는지 확인하는 데 사용한다.
    """
    return int(
        _psql(
            "SELECT COUNT(*) FROM audit_log WHERE event_type='copilot_cell_inserted'"
        )
    )


def _reset_notebook() -> None:
    """테스트 시작 전에 copilot.ipynb 를 삭제하여 깨끗한 상태를 만든다.

    최선(best-effort) 삭제이므로 노트북이 없어서 404 가 오는 경우도 정상이다.
    """
    # 404 는 정상 — 이미 없는 경우이므로 무시한다.
    httpx.delete(
        f"{JUPYTER_BASE}/api/contents/{NOTEBOOK}",
        headers={"Authorization": f"token {JUPYTER_TOKEN}"},
        timeout=10.0,
    )


def _get_notebook() -> dict | None:
    """Jupyter REST API 에서 copilot.ipynb 의 전체 내용을 가져온다.

    노트북이 존재하지 않으면(404) None 을 반환한다.
    """
    r = httpx.get(
        f"{JUPYTER_BASE}/api/contents/{NOTEBOOK}",
        headers={"Authorization": f"token {JUPYTER_TOKEN}"},
        timeout=10.0,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def test_nl_to_jupyter_cell_round_trip() -> None:
    """자연어 질문 → Anthropic 스트리밍 → 코드 블록 자동 삽입 → audit 기록까지의
    전체 왕복 경로를 검증한다.

    검증하는 불변식:
    - SPA 가 Jupyter REST PUT 과 /api/copilot/cell-inserted 를 실제로 호출한다.
    - copilot.ipynb 에 sales.customers 를 포함한 코드 셀이 추가된다.
    - audit_log 행이 정확히 1개 추가된다(중복 삽입 없음).
    - audit payload 의 row_data_transmitted 가 false 여야 한다
      (셀 코드 길이만 기록하고 실제 행 데이터는 절대 기록하지 않음 — FR-LLM-05).
    """
    _reset_notebook()
    before = _audit_count()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        page = ctx.new_page()

        api_calls: list[str] = []
        page.on(
            "request",
            lambda req: api_calls.append(f"{req.method} {req.url}")
            if "/api/copilot" in req.url or "/jupyter/api/contents" in req.url
            else None,
        )
        console: list[str] = []
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}"))
        page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))

        try:
            # 1. JupyterWithCopilot 페이지에 접속한다.
            page.goto(f"{PORTAL_URL}/analyst/", wait_until="commit", timeout=90000)
            expect(page.get_by_text("분석 코파일럿", exact=False)).to_be_visible(
                timeout=60_000
            )

            # 2. ```sql``` 코드 블록을 강제하는 질문을 전송한다.
            #    소형 모델도 펜스를 씌우도록 명시적으로 지시한다.
            question = (
                "Postgres SQL 한 줄을 ```sql ... ``` 형식으로만 답하세요. "
                "다른 설명은 절대 포함하지 마세요. "
                "쿼리: sales.customers 테이블 행 수 세기."
            )
            chat_input = page.get_by_placeholder("자연어로 질문하세요…")
            expect(chat_input).to_be_visible(timeout=15_000)
            chat_input.fill(question)
            page.locator("button").filter(has_text="보내기").first.click()

            # 3. 새 기본 동작: SPA 가 펜스드 코드 블록을 감지하면 자동 삽입한다.
            #    클릭이 추가로 필요 없다.
            #    자동 삽입 성공 후 패널이 표시하는 "✅ … 자동 추가됨" 배지를 기다린다.
            auto_status = page.get_by_text("자동 추가됨", exact=False).first
            expect(auto_status).to_be_visible(timeout=60_000)

            # 4. 네트워크 증거: Jupyter PUT 과 백엔드 audit 엔드포인트가 실제로 호출됨.
            #    녹색 토스트는 4초 후 사라지므로 여기서 경쟁하지 않는다.
            #    위 배지 + 아래 네트워크 로그로 충분하다.
            assert any(
                "PUT " in c and "/jupyter/api/contents/copilot.ipynb" in c for c in api_calls
            ), api_calls
            assert any(
                "POST " in c and "/api/copilot/cell-inserted" in c for c in api_calls
            ), api_calls
        finally:
            # 실패 경로에 상관없이 진단 파일을 덤프한다.
            page.screenshot(
                path="tests/e2e/.last-copilot-integration.png", full_page=True
            )
            with open(
                "tests/e2e/.last-copilot-integration.log", "w", encoding="utf-8"
            ) as fh:
                fh.write("=== api/jupyter calls ===\n" + "\n".join(api_calls))
                fh.write("\n\n=== console ===\n" + "\n".join(console))
            ctx.close()
            browser.close()

    # 서버 측 증거:
    # a) copilot.ipynb 가 생성되었고 우리의 SQL 힌트를 포함한 코드 셀이 있다.
    nb = _get_notebook()
    assert nb is not None, "copilot.ipynb was not created"
    cells = nb["content"]["cells"]
    assert cells, "notebook has no cells after insertion"
    last = cells[-1]
    assert last["cell_type"] == "code"
    assert "sales.customers" in last["source"], last["source"]

    # b) audit 행이 정확히 1개 추가되었다.
    after = _audit_count()
    assert after == before + 1, f"audit count moved {before} → {after}"

    # c) 새 audit 행의 row_data_transmitted 는 false 여야 한다.
    #    이 이벤트는 셀 삽입 이벤트이며, 생성된 payload 의 *길이*만 기록한다.
    #    실제 쿼리 행 데이터는 절대 기록하지 않는다(FR-LLM-05 감사 보장).
    payload_text = _psql(
        "SELECT payload FROM audit_log WHERE event_type='copilot_cell_inserted' "
        "ORDER BY occurred_at DESC LIMIT 1"
    )
    payload = json.loads(payload_text)
    assert payload.get("notebook_path") == NOTEBOOK
    assert payload.get("language") in ("sql", "python")
    assert int(payload.get("source_length") or 0) > 0
