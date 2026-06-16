"""Follow-up turn: 'refactor the cell you just wrote' must work.

This proves the new behaviour:
    1) The chat answer to a code-generation request does NOT show the code
       body anymore — only a short narration + "셀 추가됨" badge.
    2) The second turn that says "이 코드 리팩토링 해줘" includes the
       existing copilot.ipynb cell sources in the API payload, and the
       resulting assistant message contains another code block (the refactor)
       which is auto-inserted as a new cell.
"""

from __future__ import annotations

import json
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


def _get_cells() -> list[dict]:
    r = httpx.get(
        f"{JUPYTER_BASE}/api/contents/{NOTEBOOK}",
        headers={"Authorization": f"token {JUPYTER_TOKEN}"},
        timeout=10.0,
    )
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()["content"]["cells"]


def _send(page, q: str) -> None:
    page.get_by_placeholder("자연어로 질문하세요…").fill(q)
    page.locator("button").filter(has_text="보내기").first.click()


def test_followup_refactor_includes_prior_cells_and_hides_code_body() -> None:
    _reset_notebook()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        page = ctx.new_page()

        # Capture every copilot/chat payload + every jupyter PUT so we can
        # tell whether turn-2's PUT actually fired and what it sent.
        chat_payloads: list[dict] = []
        jupyter_puts: list[dict] = []
        console_msgs: list[str] = []

        def on_request(req):
            if req.url.endswith("/api/copilot/chat") and req.method == "POST":
                try:
                    body = req.post_data
                    if body:
                        chat_payloads.append(json.loads(body))
                except Exception:
                    pass
            if "/jupyter/api/contents/copilot.ipynb" in req.url and req.method == "PUT":
                try:
                    body = req.post_data
                    cells = json.loads(body)["content"]["cells"] if body else []
                    jupyter_puts.append(
                        {"url": req.url, "cell_count": len(cells)}
                    )
                except Exception as e:
                    jupyter_puts.append({"url": req.url, "parse_error": str(e)})

        page.on("request", on_request)
        page.on("console", lambda m: console_msgs.append(f"{m.type}: {m.text[:300]}"))
        page.on("pageerror", lambda e: console_msgs.append(f"pageerror: {e}"))

        try:
            page.goto(f"{PORTAL_URL}/analyst/", wait_until="commit", timeout=90000)
            expect(page.get_by_text("분석 코파일럿", exact=False)).to_be_visible(
                timeout=60_000
            )

            # Turn 1: generate the initial SQL cell. We avoid putting triple
            # backticks in the question itself (it would show up verbatim in
            # the user bubble and trip the "no raw fence" assertion below).
            _send(
                page,
                "Postgres SQL 한 줄을 SQL 코드 블록으로만 답하세요. "
                "다른 설명은 절대 포함하지 마세요. "
                "쿼리: sales.customers 테이블 행 수 세기.",
            )
            expect(
                page.get_by_text("셀이 copilot.ipynb 에 추가됨", exact=False).first
            ).to_be_visible(timeout=60_000)

            # The ASSISTANT card must NOT print the raw ```sql ... ``` body —
            # we now hide it and only show the badge + (optional) narration.
            # User bubbles are fine to contain whatever the user typed.
            assistant_card = page.locator("text=코파일럿").locator(
                "xpath=ancestor::*[contains(@class,'mantine-Card-root')]"
            ).first
            assistant_text = assistant_card.inner_text()
            assert "```sql" not in assistant_text, (
                "raw code fence is leaking into the assistant card:\n"
                + assistant_text[:400]
            )
            # Badge text is uppercased by Mantine CSS; case-insensitive check.
            # (Badge says "노트북에" since the insert target is now the
            # *active* notebook, not a hardcoded copilot.ipynb.)
            lower = assistant_text.lower()
            assert "셀이 노트북에" in lower, assistant_text
            assert "자동 추가됨" in lower, assistant_text

            # Server-side: at least one code cell now exists with our SQL.
            cells = _get_cells()
            code_cells = [c for c in cells if c["cell_type"] == "code"]
            assert code_cells, "no code cells after turn 1"
            prior_source = code_cells[-1]["source"]
            assert "sales.customers" in prior_source, prior_source

            # Turn 2: ask for a refactor that should reference the existing
            # cell. We don't restate the SQL — the SPA must inject it.
            _send(
                page,
                "방금 만든 셀을 리팩토링해서 도시별 고객 수를 함께 보여주는 "
                "Postgres SQL로 바꿔 주세요. SQL 코드 블록 한 개만 답하세요.",
            )

            # Wait for a SECOND auto-insert badge — meaning the refactor
            # came back with a code block and was inserted as a new cell.
            # `i` flag because Mantine renders the filename uppercased via CSS
            # and innerText reflects the rendered casing.
            page.wait_for_function(
                "() => (document.body.innerText.match(/셀이 노트북에 자동 추가됨/gi) || []).length >= 2",
                timeout=120_000,
            )

            # The second API call must have carried the prior cell text in
            # its `question` field (that's how the model knows what to refactor).
            assert len(chat_payloads) >= 2, chat_payloads
            second = chat_payloads[1]
            assert "sales.customers" in second["question"], (
                "turn-2 payload didn't carry the prior cell context:\n"
                + second["question"][:600]
            )
            assert "copilot.ipynb" in second["question"], second["question"][:600]

            # Server side: another code cell was added. The badge is painted
            # by React before the actual PUT resolves, so poll for up to 15 s.
            import time as _t
            deadline = _t.time() + 15
            code_after: list[dict] = []
            while _t.time() < deadline:
                cells_after = _get_cells()
                code_after = [c for c in cells_after if c["cell_type"] == "code"]
                if len(code_after) > len(code_cells):
                    break
                _t.sleep(0.5)
            assert len(code_after) > len(code_cells), (
                f"expected more code cells after refactor: "
                f"{len(code_cells)} → {len(code_after)}"
            )
        finally:
            page.screenshot(
                path="tests/e2e/.last-copilot-refactor.png", full_page=True
            )
            ctx.close()
            browser.close()
