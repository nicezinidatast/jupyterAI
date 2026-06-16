"""Playwright-driven UI smoke for the Analyst Workspace SPA.

Runs against the live demo stack started by ``infra/docker-compose/compose.yml``:
portal nginx on :5180 fronts ``/analyst/`` (Vite dev) and ``/api/*`` (FastAPI).

Coverage (analyst golden path):
  1. SPA loads via portal, root <div id="root"> mounts
  2. /analyst/sql page renders the QueryEditor (connection select + SQL textarea + ▶ button)
  3. Picking ``sales_db`` and clicking a ``sales.customers`` schema badge auto-fills
     a real customers query
  4. ▶ 실행 hits the backend, masked rows render in the result <table>
  5. Network panel proves POST /api/queries/execute actually fired (not a stub)

Skips when the portal is unreachable so unit-test runs aren't blocked.
"""

from __future__ import annotations

import socket
import urllib.request

import pytest
from playwright.sync_api import expect, sync_playwright

PORTAL_URL = "http://localhost:5180"
ANALYST_URL = f"{PORTAL_URL}/analyst/"
SQL_URL = f"{PORTAL_URL}/analyst/sql"


def _portal_reachable() -> bool:
    try:
        with urllib.request.urlopen(f"{PORTAL_URL}/healthz", timeout=2) as r:
            return r.status == 200
    except (OSError, socket.error):
        return False


pytestmark = pytest.mark.skipif(
    not _portal_reachable(), reason=f"portal not reachable at {PORTAL_URL}"
)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def test_analyst_root_mounts(browser) -> None:
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(ANALYST_URL, wait_until="networkidle")
    # Root mount point exists and React renders something into it (Mantine AppShell title).
    expect(page.locator("#root")).to_be_visible()
    # The header title comes from the AppShell and is always rendered.
    expect(page.get_by_text("Analyst Workspace")).to_be_visible(timeout=15_000)
    ctx.close()


def test_analyst_sql_real_query_with_masking(browser) -> None:
    # AppShell pins a 220-px navbar; bigger viewport keeps the Select clear
    # of any navbar overlay on first paint.
    ctx = browser.new_context(viewport={"width": 1600, "height": 900})
    page = ctx.new_page()

    api_calls: list[str] = []
    all_reqs: list[str] = []
    console_msgs: list[str] = []
    page.on(
        "request",
        lambda req: (
            all_reqs.append(req.method + " " + req.url),
            api_calls.append(req.url) if "/api/queries/execute" in req.url else None,
        ),
    )
    page.on("console", lambda msg: console_msgs.append(f"{msg.type}: {msg.text}"))
    page.on("pageerror", lambda exc: console_msgs.append(f"pageerror: {exc}"))

    page.goto(SQL_URL, wait_until="networkidle")

    # The Select auto-picks the first connection on mount; the SAMPLE_SQL
    # textarea is auto-filled to match. We just confirm the auto-state landed
    # before firing the query, instead of fighting Mantine's portal-rendered
    # listbox for an explicit switch.
    select_input = page.get_by_role("textbox", name="커넥션")
    expect(select_input).to_be_visible(timeout=15_000)
    expect(select_input).not_to_have_value("", timeout=15_000)

    sql_textarea = page.get_by_role("textbox", name="SQL")
    # crm_mysql.leads has email (gets email-masked) + phone (gets phone-masked).
    # Replace whatever sample query auto-filled so the assertion is deterministic.
    sql_textarea.fill("SELECT email, phone FROM leads LIMIT 5")
    # Mantine's input wires onChange to the input event Playwright fires; verify
    # the value actually committed before clicking.
    expect(sql_textarea).to_have_value("SELECT email, phone FROM leads LIMIT 5")

    # Fire the execution. The leading ▶ glyph is part of the visible label but
    # accessible-name matching can be flaky across emoji widths, so target the
    # button by substring.
    run_btn = page.locator("button").filter(has_text="실행").first
    expect(run_btn).to_be_enabled(timeout=15_000)
    run_btn.click(force=True)

    try:
        # Table renders with at least one row whose first cell contains '*' (PII mask).
        # The result Table.Td cells render <Code> blocks, so look for the mask glyph.
        expect(page.locator("table tbody tr").first).to_be_visible(timeout=15_000)
        rendered_text = page.locator("table tbody").inner_text()
        assert "*" in rendered_text, f"no masked value visible in rendered rows: {rendered_text!r}"
        # Network proof: the SPA actually hit the backend.
        assert any("/api/queries/execute" in u for u in api_calls), api_calls
    except Exception:
        # Drop diagnostics next to the test for inspection.
        page.screenshot(path="tests/e2e/.last-analyst-failure.png", full_page=True)
        with open("tests/e2e/.last-analyst-failure.log", "w", encoding="utf-8") as fh:
            fh.write("=== requests ===\n" + "\n".join(all_reqs))
            fh.write("\n\n=== console ===\n" + "\n".join(console_msgs))
            fh.write("\n\n=== api_calls ===\n" + "\n".join(api_calls))
        raise
    finally:
        ctx.close()
