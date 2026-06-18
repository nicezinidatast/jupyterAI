"""활성 노트북 셀 타겟팅 + chat-squish 회귀 테스트 (e2e).

시나리오:
    1. Jupyter REST API 로 ``analysis-scratch.ipynb`` 를 (재)생성한다.
    2. SPA 내부 JupyterLab에서 ``docmanager:open`` 커맨드(window.jupyterapp —
       --LabApp.expose_app_in_browser 플래그로 노출)를 통해 해당 노트북을 연다.
    3. 코파일럿에 ```sql``` 코드 블록 응답을 강제하는 질문을 전송한다.
    4. 생성된 셀은 기본값인 copilot.ipynb 가 아닌 *analysis-scratch.ipynb*
       (현재 활성 노트북)에 삽입되어야 한다.
    5. audit_log 행의 notebook_path 가 analysis-scratch.ipynb 를 가리켜야 한다.
    6. Chat-squish 회귀: 히스토리가 넘쳐도 메시지 카드가 flex로 압축되어서는 안 된다
       (clientHeight >= scrollHeight 불변식).

실제 서비스 전용 — portal 이나 Anthropic provider 가 없으면 자동 skip된다
(test_copilot_integration 과 동일한 skip 정책).
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
    """Jupyter REST API 로 scratch 노트북을 (재)생성한다.

    테스트 시작 전에 깨끗한 상태를 보장하기 위해 항상 PUT 으로 덮어쓴다.
    마커 셀(# scratch marker cell)이 포함된 최소 구조의 노트북을 생성한다.
    """
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
    """Jupyter REST API 에서 지정 노트북의 셀 목록을 가져온다.

    노트북이 아직 존재하지 않으면(404) 빈 리스트를 반환한다.
    """
    r = httpx.get(
        f"{JUPYTER_BASE}/api/contents/{path}", headers=_HEADERS, timeout=15.0
    )
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()["content"]["cells"]


def test_cell_lands_in_active_notebook() -> None:
    """생성된 셀이 copilot.ipynb 가 아닌 현재 활성 노트북에 삽입됨을 검증한다.

    검증하는 불변식:
    - 코파일럿 셀 삽입은 항상 JupyterLab 의 현재 활성 노트북을 대상으로 해야 한다.
    - 활성 노트북이 scratch 인 경우 copilot.ipynb 의 셀 수는 변하지 않아야 한다.
    - audit_log 의 notebook_path 가 실제 삽입 대상을 기록해야 한다.
    - chat 메시지 카드가 flex로 압축되지 않아야 한다(chat-squish 회귀).
    """
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

            # iframe 내부의 JupyterLab 이 부팅될 때까지 대기한 뒤,
            # window.jupyterapp 이 노출되어 있는지 확인한다
            # (docker-compose의 --LabApp.expose_app_in_browser=True 플래그 필요).
            # 그다음 scratch 노트북을 열어 *활성* main-area 위젯으로 만든다.
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
            # docmanager:open 은 비동기이므로, scratch 탭이 VISIBLE 상태인
            # main-area 위젯이 될 때까지 폴링한다.
            # shell.currentWidget 은 포커스 트래커 기반이라 실제 브라우저 포커스를
            # 받지 못하는 헤드리스 iframe 에서는 null 로 남을 수 있다.
            # (SPA의 getActiveNotebookPanel 도 동일한 isVisible 폴백을 사용한다.)
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

            # 펜스드 SQL 답변을 강제하는 질문을 전송한다.
            # 스키마에 무관한 상수 쿼리를 사용하는 이유: 코파일럿은 활성 커넥션의
            # 스키마 컨텍스트를 주입하므로, 존재하지 않는 테이블을 묻는 질문은
            # 모델이 코드 블록 대신 거절 응답을 내놓을 수 있다.
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
            # context.save() 가 디스크에 플러시할 시간을 준 후 REST API 로 읽는다.
            page.wait_for_timeout(1500)

            # Chat-squish 회귀 검증: 어떤 메시지 카드도 flex로 압축되어서는 안 된다.
            # scrollHeight > clientHeight + 1 인 카드가 있으면 압축된 것이다.
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

    # 서버 측 증거 1: 생성된 셀이 scratch 노트북에 들어갔는지 확인한다.
    scratch_cells = _get_cells(SCRATCH)
    assert len(scratch_cells) >= 2, "no cell was appended to the scratch notebook"
    last = scratch_cells[-1]
    assert last["cell_type"] == "code"
    src = last["source"] if isinstance(last["source"], str) else "".join(last["source"])
    assert "42" in src, src
    assert src.startswith("%%sql"), src

    # 서버 측 증거 2: copilot.ipynb 는 삽입 대상이 아니어야 한다.
    assert len(_get_cells("copilot.ipynb")) == copilot_cells_before

    # 서버 측 증거 3: audit_log 가 실제 삽입 대상 노트북을 기록해야 한다.
    payload = json.loads(
        _psql(
            "SELECT payload FROM audit_log WHERE event_type='copilot_cell_inserted' "
            "ORDER BY occurred_at DESC LIMIT 1"
        )
    )
    assert payload.get("notebook_path") == SCRATCH, payload
