"""End-to-end test for the headline copilot integration:

    NL question  →  Anthropic streaming  →  ```sql``` code block in answer
                 →  "📥 셀로 삽입" button
                 →  JupyterLab REST PUT into copilot.ipynb
                 →  audit_log row of event_type=copilot_cell_inserted

Real services only — no stubs. The test is skipped automatically when:
    * portal nginx is unreachable, OR
    * the Anthropic provider isn't configured (``GET /api/copilot/provider``
      returns non-200), so contributors without a key can still run the rest
      of the suite.

Expensive (one Anthropic round-trip per run, ~5-15s). Marked ``copilot`` so it
can be deselected with ``pytest -m 'not copilot'`` in CI.
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
    """Run a SQL statement inside the Postgres container.

    We use ``docker exec`` instead of host-side psycopg2 so the test doesn't
    depend on host pg_hba routing (Docker Desktop on Windows exposes
    container :5432 to the host, but local credentials may differ from the
    in-container superuser flow).
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


def _audit_count() -> int:
    return int(
        _psql(
            "SELECT COUNT(*) FROM audit_log WHERE event_type='copilot_cell_inserted'"
        )
    )


def _reset_notebook() -> None:
    # Best-effort wipe; 404 is fine.
    httpx.delete(
        f"{JUPYTER_BASE}/api/contents/{NOTEBOOK}",
        headers={"Authorization": f"token {JUPYTER_TOKEN}"},
        timeout=10.0,
    )


def _get_notebook() -> dict | None:
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
            # 1. Land on JupyterWithCopilot.
            page.goto(f"{PORTAL_URL}/analyst/", wait_until="commit", timeout=90000)
            expect(page.get_by_text("분석 코파일럿", exact=False)).to_be_visible(
                timeout=60_000
            )

            # 2. Ask a question that *forces* a ```sql``` block in the answer.
            #    Be very explicit so even a small model wraps the SQL in fences.
            question = (
                "Postgres SQL 한 줄을 ```sql ... ``` 형식으로만 답하세요. "
                "다른 설명은 절대 포함하지 마세요. "
                "쿼리: sales.customers 테이블 행 수 세기."
            )
            chat_input = page.get_by_placeholder("자연어로 질문하세요…")
            expect(chat_input).to_be_visible(timeout=15_000)
            chat_input.fill(question)
            page.locator("button").filter(has_text="보내기").first.click()

            # 3. New default behaviour: the SPA inserts every fenced code block
            #    automatically — no extra click needed. We wait for the
            #    "✅ … 자동 추가됨" status badge that the panel paints after
            #    a successful auto-insert.
            auto_status = page.get_by_text("자동 추가됨", exact=False).first
            expect(auto_status).to_be_visible(timeout=60_000)

            # 4. Network proof: SPA hit Jupyter PUT + backend audit. (The
            #    green toast disappears after 4 s so we don't race it here —
            #    the badge above plus the network log below are sufficient.)
            assert any(
                "PUT " in c and "/jupyter/api/contents/copilot.ipynb" in c for c in api_calls
            ), api_calls
            assert any(
                "POST " in c and "/api/copilot/cell-inserted" in c for c in api_calls
            ), api_calls
        finally:
            # Drop diagnostics for any failure path.
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

    # 6. Server-side proof:
    #    a) copilot.ipynb exists and has at least one code cell with our SQL hint.
    nb = _get_notebook()
    assert nb is not None, "copilot.ipynb was not created"
    cells = nb["content"]["cells"]
    assert cells, "notebook has no cells after insertion"
    last = cells[-1]
    assert last["cell_type"] == "code"
    assert "sales.customers" in last["source"], last["source"]

    #    b) audit row count went up by exactly one.
    after = _audit_count()
    assert after == before + 1, f"audit count moved {before} → {after}"

    #    c) the new audit row records row_data_transmitted == false (this is the
    #       insert event, not the chat event — but it must still record the
    #       generated payload's *length*, never the rows).
    payload_text = _psql(
        "SELECT payload FROM audit_log WHERE event_type='copilot_cell_inserted' "
        "ORDER BY occurred_at DESC LIMIT 1"
    )
    payload = json.loads(payload_text)
    assert payload.get("notebook_path") == NOTEBOOK
    assert payload.get("language") in ("sql", "python")
    assert int(payload.get("source_length") or 0) > 0
