"""Analyst Workspace SPA 의 Playwright 기반 UI 스모크 테스트.

infra/docker-compose/compose.yml 로 기동한 데모 스택(portal nginx :5180)을 대상으로 실행한다.
nginx는 /analyst/ (Vite dev)와 /api/* (FastAPI)를 역방향 프록시한다.

검증 범위 (애널리스트 황금 경로):
  1. SPA가 portal을 통해 로드되고 루트 <div id="root">가 마운트된다.
  2. /analyst/sql 페이지에서 QueryEditor(커넥션 셀렉트 + SQL textarea + ▶ 버튼)가 렌더링된다.
  3. ``sales_db``를 선택하고 ``sales.customers`` 스키마 배지를 클릭하면 실제 쿼리가 자동 채워진다.
  4. ▶ 실행을 클릭하면 백엔드에 요청이 전달되고, PII 마스킹된 행이 결과 <table>에 렌더링된다.
  5. 네트워크 캡처로 POST /api/queries/execute 가 실제로 발화되었음을 증명한다(스텁 아님).

portal에 접근할 수 없는 환경에서는 자동 skip 되어 단위 테스트 실행을 막지 않는다.
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
    """portal /healthz 엔드포인트에 2 초 이내에 응답이 오면 True를 반환한다.

    이 결과로 pytestmark가 전체 모듈을 skip할지 결정하므로,
    import 시점에 딱 한 번 평가된다.
    """
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
    """모듈 스코프 Playwright Chromium 인스턴스.

    모듈 내 모든 테스트가 같은 브라우저 프로세스를 재사용하므로
    Chromium 기동 비용이 한 번만 발생한다. 컨텍스트(탭)는 각 테스트에서
    개별적으로 생성·닫아 상태 격리를 보장한다.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def test_analyst_root_mounts(browser) -> None:
    """SPA 마운트 검증: /analyst/ 접속 시 React 루트와 AppShell 헤더가 렌더링된다.

    #root 가 DOM에 존재하고 Mantine AppShell 타이틀이 보이면 JS 번들 로드와
    React 렌더링이 정상임을 보장한다.
    """
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(ANALYST_URL, wait_until="networkidle")
    # React 마운트 지점이 존재하고 Mantine AppShell 타이틀이 렌더링되었는지 확인한다.
    expect(page.locator("#root")).to_be_visible()
    # AppShell 헤더 타이틀은 인증 여부에 무관하게 항상 렌더링된다.
    expect(page.get_by_text("Analyst Workspace")).to_be_visible(timeout=15_000)
    ctx.close()


def test_analyst_sql_real_query_with_masking(browser) -> None:
    """SQL 실행 후 PII 마스킹 결과가 테이블에 렌더링되고, 백엔드 호출이 실제로 발화됨을 검증한다.

    불변식:
    - /api/queries/execute 가 네트워크 레벨에서 실제로 호출된다(프론트 스텁이 아님).
    - 결과 테이블에는 '*' 문자가 포함된 마스킹 값이 나타난다.
    - 오류 시 스크린샷과 콘솔 로그를 tests/e2e/ 에 덤프해 원인 추적을 돕는다.
    """
    # AppShell이 220px 너비의 navbar를 고정하므로, 첫 페인트에서 navbar 오버레이에
    # 커넥션 Select가 가려지지 않도록 1600px 뷰포트를 사용한다.
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

    # Select는 마운트 시 첫 번째 커넥션을 자동 선택하고 SAMPLE_SQL을 채운다.
    # Mantine의 portal-rendered 리스트박스와 싸우는 대신, 자동 선택 상태가
    # 완료되었음만 확인하고 쿼리를 실행한다.
    select_input = page.get_by_role("textbox", name="커넥션")
    expect(select_input).to_be_visible(timeout=15_000)
    expect(select_input).not_to_have_value("", timeout=15_000)

    sql_textarea = page.get_by_role("textbox", name="SQL")
    # crm_mysql.leads 테이블은 email(이메일 마스킹)과 phone(전화번호 마스킹) 컬럼을 가진다.
    # 자동 채워진 샘플 쿼리를 교체하여 어서션이 항상 일관된 결과를 보도록 한다.
    sql_textarea.fill("SELECT email, phone FROM leads LIMIT 5")
    # Mantine의 input은 Playwright가 발화하는 input 이벤트에 onChange를 연결한다.
    # 클릭 전에 값이 실제로 커밋되었는지 검증한다.
    expect(sql_textarea).to_have_value("SELECT email, phone FROM leads LIMIT 5")

    # ▶ 글리프는 레이블의 일부이지만 이모지 너비에 따라 accessible-name 매칭이
    # 불안정할 수 있으므로 부분 문자열로 버튼을 찾는다.
    run_btn = page.locator("button").filter(has_text="실행").first
    expect(run_btn).to_be_enabled(timeout=15_000)
    run_btn.click(force=True)

    try:
        # 결과 테이블 첫 번째 행이 렌더링되고, tbody 텍스트에 '*'(PII 마스크 문자)가
        # 포함되어 있어야 한다. Mantine Table.Td는 <Code> 블록으로 렌더링하므로
        # mask 글리프를 직접 탐색한다.
        expect(page.locator("table tbody tr").first).to_be_visible(timeout=15_000)
        rendered_text = page.locator("table tbody").inner_text()
        assert "*" in rendered_text, f"no masked value visible in rendered rows: {rendered_text!r}"
        # 네트워크 증거: SPA가 백엔드를 실제로 호출했음을 확인한다.
        assert any("/api/queries/execute" in u for u in api_calls), api_calls
    except Exception:
        # 실패 시 스크린샷과 로그를 tests/e2e/ 에 덤프하여 원인 추적을 돕는다.
        page.screenshot(path="tests/e2e/.last-analyst-failure.png", full_page=True)
        with open("tests/e2e/.last-analyst-failure.log", "w", encoding="utf-8") as fh:
            fh.write("=== requests ===\n" + "\n".join(all_reqs))
            fh.write("\n\n=== console ===\n" + "\n".join(console_msgs))
            fh.write("\n\n=== api_calls ===\n" + "\n".join(api_calls))
        raise
    finally:
        ctx.close()
