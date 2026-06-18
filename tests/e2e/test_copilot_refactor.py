"""후속 턴 '방금 쓴 셀을 리팩토링 해줘' 가 올바르게 동작하는지 검증하는 e2e 테스트.

이 테스트가 보장하는 새 동작:
    1) 코드 생성 요청에 대한 어시스턴트 답변에서 코드 본문이 더 이상 노출되지 않는다
       — 짧은 서술 + "셀 추가됨" 배지만 표시된다.
    2) "이 코드 리팩토링 해줘" 두 번째 턴은 기존 copilot.ipynb 셀 소스를
       API 페이로드에 포함하고, 어시스턴트 답변에 또 다른 코드 블록(리팩토링 결과)이
       들어 있으며 새 셀로 자동 삽입된다.
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
    """테스트 전에 copilot.ipynb 를 삭제해 깨끗한 상태로 만든다.

    404 는 무시한다(이미 없는 경우).
    """
    httpx.delete(
        f"{JUPYTER_BASE}/api/contents/{NOTEBOOK}",
        headers={"Authorization": f"token {JUPYTER_TOKEN}"},
        timeout=10.0,
    )


def _get_cells() -> list[dict]:
    """copilot.ipynb 의 셀 목록을 반환한다. 노트북이 없으면 빈 리스트를 반환한다."""
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
    """채팅 입력창에 질문을 채우고 전송 버튼을 클릭한다."""
    page.get_by_placeholder("자연어로 질문하세요…").fill(q)
    page.locator("button").filter(has_text="보내기").first.click()


def test_followup_refactor_includes_prior_cells_and_hides_code_body() -> None:
    """리팩토링 후속 턴이 이전 셀 컨텍스트를 포함하고, 어시스턴트 카드에 코드가 노출되지 않음을 검증한다.

    검증하는 불변식:
    - 어시스턴트 카드에 raw ```sql ... ``` 펜스가 노출되지 않는다(UX 계약).
    - 두 번째 API 요청 payload 의 question 필드에 이전 셀 소스가 포함된다
      (SPA 가 컨텍스트 주입 의무를 이행했음을 증명).
    - 리팩토링 결과로 새 코드 셀이 노트북에 추가된다.
    """
    _reset_notebook()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        page = ctx.new_page()

        # copilot/chat 페이로드와 jupyter PUT 을 모두 캡처하여
        # 두 번째 턴의 PUT 이 실제로 발화되었는지, 무엇을 전송했는지 확인한다.
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

            # 턴 1: 초기 SQL 셀을 생성한다.
            # 질문 자체에 트리플 백틱을 넣지 않는 이유:
            # 사용자 버블에 그대로 표시되어 아래의 "raw fence 미노출" 어서션을 깨트릴 수 있다.
            _send(
                page,
                "Postgres SQL 한 줄을 SQL 코드 블록으로만 답하세요. "
                "다른 설명은 절대 포함하지 마세요. "
                "쿼리: sales.customers 테이블 행 수 세기.",
            )
            expect(
                page.get_by_text("셀이 copilot.ipynb 에 추가됨", exact=False).first
            ).to_be_visible(timeout=60_000)

            # 어시스턴트 카드에 raw ```sql ... ``` 본문이 노출되어서는 안 된다.
            # 새 동작에서는 코드 본문을 숨기고 배지 + (선택적) 서술만 표시한다.
            # 사용자 버블에는 사용자가 입력한 내용이 그대로 표시되어도 무방하다.
            assistant_card = page.locator("text=코파일럿").locator(
                "xpath=ancestor::*[contains(@class,'mantine-Card-root')]"
            ).first
            assistant_text = assistant_card.inner_text()
            assert "```sql" not in assistant_text, (
                "raw code fence is leaking into the assistant card:\n"
                + assistant_text[:400]
            )
            # Mantine CSS 가 배지 텍스트를 대문자로 렌더링하므로 대소문자 무시 체크.
            # (삽입 대상이 이제 하드코딩된 copilot.ipynb 가 아닌 *활성* 노트북이므로
            # 배지에 "노트북에" 가 표시된다.)
            lower = assistant_text.lower()
            assert "셀이 노트북에" in lower, assistant_text
            assert "자동 추가됨" in lower, assistant_text

            # 서버 측: 최소 하나의 코드 셀이 우리의 SQL 을 포함하고 있어야 한다.
            cells = _get_cells()
            code_cells = [c for c in cells if c["cell_type"] == "code"]
            assert code_cells, "no code cells after turn 1"
            prior_source = code_cells[-1]["source"]
            assert "sales.customers" in prior_source, prior_source

            # 턴 2: 리팩토링을 요청한다. SQL 을 다시 언급하지 않는다.
            # SPA 가 이전 셀 소스를 페이로드에 주입해야 한다.
            _send(
                page,
                "방금 만든 셀을 리팩토링해서 도시별 고객 수를 함께 보여주는 "
                "Postgres SQL로 바꿔 주세요. SQL 코드 블록 한 개만 답하세요.",
            )

            # 두 번째 자동 삽입 배지가 나타날 때까지 기다린다.
            # Mantine 이 파일명을 CSS 대문자로 렌더링하므로 `i` 플래그로 대소문자 무시.
            page.wait_for_function(
                "() => (document.body.innerText.match(/셀이 노트북에 자동 추가됨/gi) || []).length >= 2",
                timeout=120_000,
            )

            # 두 번째 API 호출의 question 필드에 이전 셀 텍스트가 포함되어야 한다.
            # 이것이 모델이 리팩토링 대상을 아는 방식이다(SPA의 컨텍스트 주입).
            assert len(chat_payloads) >= 2, chat_payloads
            second = chat_payloads[1]
            assert "sales.customers" in second["question"], (
                "turn-2 payload didn't carry the prior cell context:\n"
                + second["question"][:600]
            )
            assert "copilot.ipynb" in second["question"], second["question"][:600]

            # 서버 측: 추가 코드 셀이 삽입되었는지 확인한다.
            # React 가 실제 PUT 완료 전에 배지를 먼저 표시하므로 최대 15초 폴링한다.
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
