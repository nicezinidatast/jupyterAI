"""End-to-end test for the FULL user-visible round-trip:

    NL question → Anthropic streaming → ```sql``` code block in answer
                → auto-insert PUT to copilot.ipynb
                → JupyterLab iframe reloads
                → the new cell's source ("sales.customers") is actually
                  visible inside the embedded JupyterLab UI

This is what the user means by "코드 바로 주피터 셀에 삽입되게 해달라". The
older `test_copilot_integration.py` only proves the server-side PUT/audit
trail; this one also proves the iframe shows the cell to the analyst.
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
    try:
        with urllib.request.urlopen(f"{PORTAL_URL}/healthz", timeout=8) as r:
            return r.status == 200
    except (OSError, socket.error):
        return False


def _anthropic_configured() -> bool:
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
    httpx.delete(
        f"{JUPYTER_BASE}/api/contents/{NOTEBOOK}",
        headers={"Authorization": f"token {JUPYTER_TOKEN}"},
        timeout=10.0,
    )


def test_inserted_cell_visible_in_jupyterlab_iframe() -> None:
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

            # Ask a question that will deterministically include "sales.customers"
            # inside a ```sql``` fence so we know what text to look for in the UI.
            question = (
                "Postgres SQL 한 줄을 ```sql ... ``` 형식으로만 답하세요. "
                "다른 설명은 절대 포함하지 마세요. "
                "쿼리: sales.customers 테이블의 행 수 세기."
            )
            chat_input = page.get_by_placeholder("자연어로 질문하세요…")
            expect(chat_input).to_be_visible(timeout=15_000)
            chat_input.fill(question)
            page.locator("button").filter(has_text="보내기").first.click()

            # Auto-insert badge appears once the PUT lands.
            expect(
                page.get_by_text("자동 추가됨", exact=False).first
            ).to_be_visible(timeout=60_000)
            expect(
                page.get_by_text("셀이 copilot.ipynb 에 추가됨", exact=False)
            ).to_be_visible(timeout=15_000)

            # The iframe reload is driven by the parent bumping its key — give
            # JupyterLab time to remount, open copilot.ipynb, and paint cells.
            jupyter = page.frame_locator("iframe[title='JupyterLab']")

            # Confirm lab actually mounted (the file-menu button is a reliable
            # "lab is alive" marker).
            expect(jupyter.locator("#jp-MainLogo, .jp-NotebookPanel-toolbar").first).to_be_visible(
                timeout=60_000
            )

            # The cell source is rendered by CodeMirror inside the notebook.
            # Wait for "sales.customers" to actually be present in the iframe DOM.
            cell_text = jupyter.get_by_text("sales.customers", exact=False).first
            expect(cell_text).to_be_visible(timeout=60_000)
        finally:
            page.screenshot(
                path="tests/e2e/.last-jupyter-visible-cell.png", full_page=True
            )
            ctx.close()
            browser.close()
