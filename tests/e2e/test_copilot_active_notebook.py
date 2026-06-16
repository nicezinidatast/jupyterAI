"""E2E for active-notebook cell targeting + chat-squish regression.

Scenario:
    1. Create ``analysis-scratch.ipynb`` via the Jupyter REST API.
    2. Open it inside the embedded JupyterLab via ``docmanager:open``
       (``window.jupyterapp`` — exposed with --LabApp.expose_app_in_browser).
    3. Ask the copilot a question that forces a ```sql``` block.
    4. The generated cell must land in *analysis-scratch.ipynb* (the active
       notebook), NOT in the default copilot.ipynb.
    5. The audit row must record notebook_path = analysis-scratch.ipynb.
    6. Chat regression: message cards must not be flex-compressed
       (clientHeight >= scrollHeight) once the history overflows.

Real services only — skipped when the portal or the Anthropic provider is
unavailable (same policy as test_copilot_integration).
"""

from __future__ import annotations

import json

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

from tests.e2e.test_copilot_integration import (
    JUPYTER_BASE,
    JUPYTER_TOKEN,
    PORTAL_URL,
    _anthropic_configured,
    _portal_reachable,
    _psql,
)

SCRATCH = "analysis-scratch.ipynb"

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

_HEADERS = {"Authorization": f"token {JUPYTER_TOKEN}"}


def _put_scratch_notebook() -> None:
    """(Re)create the scratch notebook with a single marker cell."""
    httpx.put(
        f"{JUPYTER_BASE}/api/contents/{SCRATCH}",
        headers=_HEADERS,
        json={
            "type": "notebook",
            "format": "json",
            "content": {
                "cells": [
                    {
                        "cell_type": "code",
                        "metadata": {},
                        "source": "# scratch marker cell",
                        "outputs": [],
                        "execution_count": None,
                    }
                ],
                "metadata": {
                    "kernelspec": {"name": "python3", "display_name": "Python 3"}
                },
                "nbformat": 4,
                "nbformat_minor": 5,
            },
        },
        timeout=15.0,
    ).raise_for_status()


def _get_cells(path: str) -> list[dict]:
    r = httpx.get(
        f"{JUPYTER_BASE}/api/contents/{path}", headers=_HEADERS, timeout=15.0
    )
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()["content"]["cells"]


def test_cell_lands_in_active_notebook() -> None:
    _put_scratch_notebook()
    copilot_cells_before = len(_get_cells("copilot.ipynb"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        page = ctx.new_page()
        console: list[str] = []
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}"))
        page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))

        try:
            page.goto(f"{PORTAL_URL}/analyst/", wait_until="commit", timeout=90_000)
            expect(page.get_by_text("분석 코파일럿", exact=False)).to_be_visible(
                timeout=60_000
            )

            # Wait for Lab to boot inside the iframe, then assert the app is
            # exposed (compose flag) and open the scratch notebook so it
            # becomes the *active* main-area widget.
            jupyter = page.frame_locator("iframe[title='JupyterLab']")
            expect(
                jupyter.locator("#jp-MainLogo, .jp-NotebookPanel-toolbar").first
            ).to_be_visible(timeout=90_000)

            iframe_el = page.locator("iframe[title='JupyterLab']").element_handle()
            lab = iframe_el.content_frame()
            assert lab is not None

            def app_ready() -> bool:
                return bool(
                    lab.evaluate(
                        "() => !!(window.jupyterapp && window.jupyterapp.shell)"
                    )
                )

            page.wait_for_timeout(2000)
            assert app_ready(), (
                "window.jupyterapp not exposed — is "
                "--LabApp.expose_app_in_browser=True set on the jupyter service?"
            )

            lab.evaluate(
                "path => window.jupyterapp.commands.execute('docmanager:open', {path})",
                SCRATCH,
            )
            # The open is async; poll until the scratch tab is the VISIBLE
            # main-area notebook. We don't assert on shell.currentWidget —
            # it's focus-tracker based and stays null in a headless iframe
            # that never receives real browser focus (the SPA's
            # getActiveNotebookPanel has the same isVisible fallback).
            active = ""
            for _ in range(30):
                active = lab.evaluate(
                    """path => {
                        const app = window.jupyterapp;
                        for (const w of app.shell.widgets('main')) {
                            if (w?.context?.path === path) {
                                app.shell.activateById(w.id);
                                if (w.isVisible) return path;
                            }
                        }
                        return app.shell.currentWidget?.context?.path ?? '';
                    }""",
                    SCRATCH,
                )
                if active == SCRATCH:
                    break
                page.wait_for_timeout(500)
            assert active == SCRATCH, (
                f"scratch notebook never became the visible main widget "
                f"(last seen: {active!r})"
            )

            # Ask a question that forces a fenced SQL answer. Use a
            # schema-independent constant query — the copilot injects the
            # ACTIVE connection's schema context, and a question about a
            # table that doesn't exist there makes the model (correctly)
            # refuse instead of emitting a code block.
            question = (
                "SQL 한 줄을 ```sql ... ``` 형식으로만 답하세요. "
                "다른 설명은 절대 포함하지 마세요. 스키마와 무관한 상수 쿼리입니다. "
                "쿼리: SELECT 42 AS answer"
            )
            chat_input = page.get_by_placeholder("자연어로 질문하세요…")
            expect(chat_input).to_be_visible(timeout=15_000)
            chat_input.fill(question)
            page.locator("button").filter(has_text="보내기").first.click()

            expect(
                page.get_by_text("자동 추가됨", exact=False).first
            ).to_be_visible(timeout=60_000)
            # Give context.save() a beat to flush to disk before the REST read.
            page.wait_for_timeout(1500)

            # Chat-squish regression: no message card may be flex-compressed.
            squished = page.evaluate(
                """() => {
                    const chat = document.querySelector('[data-testid="copilot-chat"]');
                    if (!chat) return ['no chat container'];
                    return [...chat.children]
                        .filter((el) => el.scrollHeight > el.clientHeight + 1)
                        .map((el) => `${el.className}: ${el.clientHeight}/${el.scrollHeight}`);
                }"""
            )
            assert squished == [], f"compressed chat cards: {squished}"
        finally:
            page.screenshot(
                path="tests/e2e/.last-active-notebook.png", full_page=True
            )
            with open(
                "tests/e2e/.last-active-notebook.log", "w", encoding="utf-8"
            ) as fh:
                fh.write("\n".join(console))
            ctx.close()
            browser.close()

    # Server-side proof: the generated cell is in the scratch notebook…
    scratch_cells = _get_cells(SCRATCH)
    assert len(scratch_cells) >= 2, "no cell was appended to the scratch notebook"
    last = scratch_cells[-1]
    assert last["cell_type"] == "code"
    src = last["source"] if isinstance(last["source"], str) else "".join(last["source"])
    assert "42" in src, src
    assert src.startswith("%%sql"), src

    # …and copilot.ipynb was NOT the insert target.
    assert len(_get_cells("copilot.ipynb")) == copilot_cells_before

    # Audit payload records the real target notebook.
    payload = json.loads(
        _psql(
            "SELECT payload FROM audit_log WHERE event_type='copilot_cell_inserted' "
            "ORDER BY occurred_at DESC LIMIT 1"
        )
    )
    assert payload.get("notebook_path") == SCRATCH, payload
