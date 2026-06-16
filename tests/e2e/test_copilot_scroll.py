"""Sticky-scroll behaviour for the Copilot chat panel.

Symptom the user reported: "채팅이 길어지면 스크롤로 위쪽 질문이 안 보임 —
스트리밍 chunk마다 강제로 끝으로 끌려내려간다."

This test verifies the fix at the smallest reliable level:
    1) Force the chat container to be scrollable (insert a tall spacer in DOM).
    2) Scroll up → the "▼ 최신 메시지로" button appears.
    3) Sending a new question re-arms autoFollow → button disappears and
       the panel pins to the bottom after the answer streams.

We don't depend on the AI generating a long answer to fill the panel — that
proved flaky. Instead we drive the scroll position directly with a spacer
and a real scroll event, which is what onScroll actually listens for.
"""

from __future__ import annotations

import socket
import urllib.request

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

PORTAL_URL = "http://localhost:5180"


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


CHAT_SEL = "[data-testid='copilot-chat']"

INSERT_SPACER_JS = """
(sel) => {
  const el = document.querySelector(sel);
  const spacer = document.createElement('div');
  spacer.setAttribute('data-test-spacer', '1');
  spacer.style.flex = '0 0 auto';
  spacer.style.height = '2000px';
  spacer.style.background = 'transparent';
  el.insertBefore(spacer, el.firstChild);
  el.scrollTop = el.scrollHeight;
}
"""

SCROLL_TO_TOP_JS = """
(sel) => {
  const el = document.querySelector(sel);
  el.scrollTop = 0;
  el.dispatchEvent(new Event('scroll'));
}
"""

APPEND_TICK_JS = """
(sel) => {
  const el = document.querySelector(sel);
  const tick = document.createElement('div');
  tick.textContent = 'tick';
  el.appendChild(tick);
}
"""


def _send(page, q: str) -> None:
    page.get_by_placeholder("자연어로 질문하세요…").fill(q)
    page.locator("button").filter(has_text="보내기").first.click()


def test_chat_scroll_sticky_pattern() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        page = ctx.new_page()

        console: list[str] = []
        page.on("console", lambda m: console.append(f"{m.type}: {m.text[:300]}"))
        page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
        try:
            page.goto(f"{PORTAL_URL}/analyst/", wait_until="commit", timeout=90000)
            try:
                expect(page.get_by_text("분석 코파일럿", exact=False)).to_be_visible(
                    timeout=60_000
                )
            except Exception:
                with open("tests/e2e/.last-copilot-scroll.console.log", "w", encoding="utf-8") as fh:
                    fh.write("\n".join(console))
                raise
            chat = page.locator(CHAT_SEL)
            expect(chat).to_be_visible(timeout=30_000)

            # Force the chat to be scrollable, then prove we're at the bottom.
            page.evaluate(INSERT_SPACER_JS, CHAT_SEL)
            metrics = chat.evaluate(
                "el => ({top: el.scrollTop, h: el.scrollHeight, c: el.clientHeight})"
            )
            assert metrics["h"] > metrics["c"] + 100, (
                f"spacer did not make panel scrollable: {metrics}"
            )
            assert metrics["h"] - metrics["top"] - metrics["c"] < 24, (
                f"after spacer insert we expected to be pinned to bottom: {metrics}"
            )
            # Button hidden because we're pinned.
            expect(page.get_by_role("button", name="▼ 최신 메시지로")).to_have_count(0)

            # Scroll up — autoFollow must flip off and the button must appear.
            page.evaluate(SCROLL_TO_TOP_JS, CHAT_SEL)
            scroll_btn = page.get_by_role("button", name="▼ 최신 메시지로")
            expect(scroll_btn).to_be_visible(timeout=5_000)
            top_after_up = chat.evaluate("el => el.scrollTop")
            assert top_after_up < 50, f"snap-back happened: top={top_after_up}"

            # Even an arbitrary DOM mutation (simulating a streaming chunk
            # arriving) must NOT yank the view back down while user is up top.
            page.evaluate(APPEND_TICK_JS, CHAT_SEL)
            page.wait_for_timeout(150)
            top_after_tick = chat.evaluate("el => el.scrollTop")
            assert top_after_tick < 50, (
                f"DOM mutation while scrolled-up snapped view down: {top_after_tick}"
            )
            expect(scroll_btn).to_be_visible()

            # Click "▼ 최신 메시지로" — must re-pin to bottom and hide itself.
            scroll_btn.click()
            page.wait_for_timeout(200)
            expect(page.get_by_role("button", name="▼ 최신 메시지로")).to_have_count(0)
            m2 = chat.evaluate(
                "el => ({top: el.scrollTop, h: el.scrollHeight, c: el.clientHeight})"
            )
            assert m2["h"] - m2["top"] - m2["c"] < 24, (
                f"click on '최신으로' did not pin to bottom: {m2}"
            )

            # Scroll up again, then send a question — the act of sending
            # must also re-arm autoFollow (separate from clicking the button).
            page.evaluate(SCROLL_TO_TOP_JS, CHAT_SEL)
            expect(scroll_btn).to_be_visible(timeout=5_000)
            _send(
                page,
                "Postgres SQL 한 줄을 ```sql ... ``` 형식으로만 답하세요. "
                "쿼리: sales.customers 행 수 세기.",
            )
            # The button should disappear as soon as send() runs setAutoFollow(true).
            expect(page.get_by_role("button", name="▼ 최신 메시지로")).to_have_count(
                0, timeout=5_000
            )
        finally:
            page.screenshot(
                path="tests/e2e/.last-copilot-scroll.png", full_page=True
            )
            ctx.close()
            browser.close()
