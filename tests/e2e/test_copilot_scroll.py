"""코파일럿 채팅 패널의 sticky-scroll 동작을 검증하는 e2e 테스트.

사용자가 보고한 증상: "채팅이 길어지면 스크롤로 위쪽 질문이 안 보임 —
스트리밍 chunk마다 강제로 끝으로 끌려내려간다."

이 테스트는 수정 사항을 가장 작고 신뢰할 수 있는 수준에서 검증한다:
    1) DOM 에 키 스페이서를 삽입해 채팅 컨테이너를 강제로 스크롤 가능한 상태로 만든다.
    2) 위로 스크롤 → "▼ 최신 메시지로" 버튼이 나타난다.
    3) 새 질문 전송이 autoFollow 를 재활성화 → 버튼이 사라지고 패널이 하단에 고정된다.

AI 가 긴 답변을 생성할 때까지 기다리는 방식은 불안정(flaky)하다는 것이 확인되었다.
대신 스페이서와 실제 scroll 이벤트로 스크롤 위치를 직접 제어한다.
이 방식은 onScroll 핸들러가 실제로 리스닝하는 것과 동일한 경로다.
"""

from __future__ import annotations

import socket
import urllib.request

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

PORTAL_URL = "http://localhost:5180"


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


CHAT_SEL = "[data-testid='copilot-chat']"

# 채팅 컨테이너 첫 번째 자식으로 2000px 높이의 투명 스페이서를 삽입하고
# 스크롤을 최하단으로 옮긴다 — 패널을 강제로 스크롤 가능한 상태로 만든다.
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

# 스크롤을 최상단으로 이동하고 scroll 이벤트를 발화한다.
# onScroll 핸들러가 autoFollow 를 비활성화하도록 scroll 이벤트가 반드시 필요하다.
SCROLL_TO_TOP_JS = """
(sel) => {
  const el = document.querySelector(sel);
  el.scrollTop = 0;
  el.dispatchEvent(new Event('scroll'));
}
"""

# 실제 스트리밍 chunk 도착 상황을 시뮬레이션: 컨테이너에 임의 DOM 노드를 추가한다.
# 사용자가 위로 스크롤해 있는 동안 이 변경이 뷰를 하단으로 끌어내리지 않아야 한다.
APPEND_TICK_JS = """
(sel) => {
  const el = document.querySelector(sel);
  const tick = document.createElement('div');
  tick.textContent = 'tick';
  el.appendChild(tick);
}
"""


def _send(page, q: str) -> None:
    """채팅 입력창에 질문을 채우고 전송 버튼을 클릭한다."""
    page.get_by_placeholder("자연어로 질문하세요…").fill(q)
    page.locator("button").filter(has_text="보내기").first.click()


def test_chat_scroll_sticky_pattern() -> None:
    """채팅 패널의 autoFollow(sticky-scroll) 동작을 검증한다.

    검증하는 불변식:
    - 스페이서 삽입 직후에는 패널이 최하단에 고정되고 "▼ 최신 메시지로" 버튼이 숨겨진다.
    - 위로 스크롤하면 autoFollow 가 비활성화되고 버튼이 나타난다.
    - autoFollow 비활성화 상태에서 DOM 변경(스트리밍 chunk 시뮬레이션)이 발생해도
      뷰가 아래로 끌려내려가지 않는다.
    - "▼ 최신 메시지로" 클릭이 패널을 최하단으로 복귀시키고 버튼을 다시 숨긴다.
    - 질문 전송이 autoFollow 를 재활성화한다(버튼 클릭과 독립적인 경로).
    """
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
                # 페이지 로드 실패 시 콘솔 로그를 파일로 덤프한다.
                with open("tests/e2e/.last-copilot-scroll.console.log", "w", encoding="utf-8") as fh:
                    fh.write("\n".join(console))
                raise
            chat = page.locator(CHAT_SEL)
            expect(chat).to_be_visible(timeout=30_000)

            # 채팅을 강제로 스크롤 가능하게 만들고, 삽입 직후 최하단에 고정됨을 확인한다.
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
            # 최하단에 고정된 상태에서는 버튼이 숨겨진다.
            expect(page.get_by_role("button", name="▼ 최신 메시지로")).to_have_count(0)

            # 위로 스크롤 → autoFollow 가 비활성화되고 버튼이 나타나야 한다.
            page.evaluate(SCROLL_TO_TOP_JS, CHAT_SEL)
            scroll_btn = page.get_by_role("button", name="▼ 최신 메시지로")
            expect(scroll_btn).to_be_visible(timeout=5_000)
            top_after_up = chat.evaluate("el => el.scrollTop")
            # snap-back 이 일어나면 top 이 0 이 아닌 값이 된다.
            assert top_after_up < 50, f"snap-back happened: top={top_after_up}"

            # 사용자가 위로 스크롤해 있는 동안 임의 DOM 변경(스트리밍 chunk 시뮬레이션)이
            # 발생해도 뷰가 하단으로 끌려내려가서는 안 된다.
            page.evaluate(APPEND_TICK_JS, CHAT_SEL)
            page.wait_for_timeout(150)
            top_after_tick = chat.evaluate("el => el.scrollTop")
            assert top_after_tick < 50, (
                f"DOM mutation while scrolled-up snapped view down: {top_after_tick}"
            )
            expect(scroll_btn).to_be_visible()

            # "▼ 최신 메시지로" 클릭 → 최하단 복귀 + 버튼 숨김.
            scroll_btn.click()
            page.wait_for_timeout(200)
            expect(page.get_by_role("button", name="▼ 최신 메시지로")).to_have_count(0)
            m2 = chat.evaluate(
                "el => ({top: el.scrollTop, h: el.scrollHeight, c: el.clientHeight})"
            )
            assert m2["h"] - m2["top"] - m2["c"] < 24, (
                f"click on '최신으로' did not pin to bottom: {m2}"
            )

            # 다시 위로 스크롤한 뒤 질문을 전송하면, 전송 행위 자체가 autoFollow 를
            # 재활성화해야 한다(버튼 클릭과는 별개의 재활성화 경로).
            page.evaluate(SCROLL_TO_TOP_JS, CHAT_SEL)
            expect(scroll_btn).to_be_visible(timeout=5_000)
            _send(
                page,
                "Postgres SQL 한 줄을 ```sql ... ``` 형식으로만 답하세요. "
                "쿼리: sales.customers 행 수 세기.",
            )
            # send() 가 setAutoFollow(true) 를 실행하는 즉시 버튼이 사라져야 한다.
            expect(page.get_by_role("button", name="▼ 최신 메시지로")).to_have_count(
                0, timeout=5_000
            )
        finally:
            page.screenshot(
                path="tests/e2e/.last-copilot-scroll.png", full_page=True
            )
            ctx.close()
            browser.close()
