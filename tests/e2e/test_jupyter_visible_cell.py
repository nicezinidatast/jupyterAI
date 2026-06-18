"""사용자가 실제로 보는 전체 왕복 경로의 end-to-end 테스트.

    자연어 질문 → Anthropic 스트리밍 → ```sql``` 코드 블록 포함 답변
                → 자동 삽입 PUT → copilot.ipynb 갱신
                → JupyterLab iframe 리로드
                → 새 셀의 소스("sales.customers")가 임베디드 JupyterLab UI 에서
                  실제로 *보여야* 한다

이것이 사용자가 "코드 바로 주피터 셀에 삽입되게 해달라"고 요청했을 때의 의도다.
기존 test_copilot_integration.py 는 서버 측 PUT/audit 경로만 증명하지만,
이 테스트는 iframe 에서 셀이 분석가에게 실제로 보임을 추가로 증명한다.
"""

from __future__ import annotations

import socket
import urllib.request

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

PORTAL_URL = "http://localhost:5180"
JUPYTER_BASE = "http://localhost:8888/jupyter"
JUPYTER_TOKEN = "dataplatform"
NOTEBOOK = "copilot.ipynb"


def _portal_reachable() -> bool:
    """portal /healthz 가 8초 이내에 200을 반환하면 True를 반환한다."""
    try:
        with urllib.request.urlopen(f"{PORTAL_URL}/healthz", timeout=8) as r:
            return r.status == 200
    except (OSError, socket.error):
        return False


def _anthropic_configured() -> bool:
    """GET /api/copilot/provider 가 provider='anthropic' 를 반환하면 True를 반환한다."""
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


def _reset_notebook() -> None:
    """테스트 전에 copilot.ipynb 를 삭제하여 깨끗한 상태로 만든다.

    404 는 이미 없는 경우이므로 무시한다.
    """
    httpx.delete(
        f"{JUPYTER_BASE}/api/contents/{NOTEBOOK}",
        headers={"Authorization": f"token {JUPYTER_TOKEN}"},
        timeout=10.0,
    )


def test_inserted_cell_visible_in_jupyterlab_iframe() -> None:
    """자동 삽입된 셀이 JupyterLab iframe UI 에서 실제로 보임을 검증한다.

    검증하는 불변식:
    - "자동 추가됨" 배지가 나타난다(PUT 완료 신호).
    - iframe 이 리마운트되고 copilot.ipynb 가 열려 셀 내용이 렌더링된다.
    - CodeMirror 셀 에디터에 "sales.customers" 텍스트가 실제로 나타난다.

    이 테스트는 test_copilot_integration.py 의 서버 측 증거에 더해,
    JupyterLab UI 에서 셀이 분석가에게 *보임*을 추가로 보장한다.
    """
    _reset_notebook()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = ctx.new_page()

        try:
            page.goto(f"{PORTAL_URL}/analyst/", wait_until="commit", timeout=90000)
            expect(page.get_by_text("분석 코파일럿", exact=False)).to_be_visible(
                timeout=60_000
            )

            # UI 에서 찾을 텍스트("sales.customers")가 답변에 반드시 포함되도록
            # 명확하게 SQL 펜스 형식을 강제하는 질문을 전송한다.
            question = (
                "Postgres SQL 한 줄을 ```sql ... ``` 형식으로만 답하세요. "
                "다른 설명은 절대 포함하지 마세요. "
                "쿼리: sales.customers 테이블의 행 수 세기."
            )
            chat_input = page.get_by_placeholder("자연어로 질문하세요…")
            expect(chat_input).to_be_visible(timeout=15_000)
            chat_input.fill(question)
            page.locator("button").filter(has_text="보내기").first.click()

            # PUT 완료 후 자동 삽입 배지가 나타난다.
            expect(
                page.get_by_text("자동 추가됨", exact=False).first
            ).to_be_visible(timeout=60_000)
            expect(
                page.get_by_text("셀이 copilot.ipynb 에 추가됨", exact=False)
            ).to_be_visible(timeout=15_000)

            # iframe 리로드는 부모 컴포넌트가 key 를 바꿔 트리거한다.
            # JupyterLab 이 리마운트되고 copilot.ipynb 를 열고 셀을 그릴 때까지 대기한다.
            jupyter = page.frame_locator("iframe[title='JupyterLab']")

            # 파일 메뉴 버튼(또는 노트북 툴바)이 나타나면 Lab 이 살아 있다는 신호다.
            expect(jupyter.locator("#jp-MainLogo, .jp-NotebookPanel-toolbar").first).to_be_visible(
                timeout=60_000
            )

            # 셀 소스는 노트북 내부의 CodeMirror 에 의해 렌더링된다.
            # iframe DOM 에 "sales.customers" 가 실제로 나타날 때까지 기다린다.
            cell_text = jupyter.get_by_text("sales.customers", exact=False).first
            expect(cell_text).to_be_visible(timeout=60_000)
        finally:
            page.screenshot(
                path="tests/e2e/.last-jupyter-visible-cell.png", full_page=True
            )
            ctx.close()
            browser.close()
