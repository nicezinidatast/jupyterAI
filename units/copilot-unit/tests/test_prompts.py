"""build_system_prompt 테스트 — 스키마 주입, PII 데이터 미포함, 테이블 렌더링."""

from __future__ import annotations

from copilot.prompts import build_system_prompt


def test_no_schema() -> None:
    p = build_system_prompt(connection_engine="postgres", schema=None)
    # 연결된 SQL DB가 없으면(=기본 워크플로) 프롬프트는 파일 기반 안내를 덧붙인다.
    # 문구는 build_system_prompt의 실제 출력("No SQL database is attached ...")과 일치시킨다.
    assert "No SQL database is attached" in p
    # 노트북 코딩 어시스턴트로서 파이썬/판다스를 안내하는지 확인한다.
    # (DB가 없으면 SQL 엔진명은 일부러 노출하지 않으므로 engine 단언은 두지 않는다.)
    assert "pandas" in p


def test_complete_analysis_directives() -> None:
    """채팅 코파일럿이 '되묻지 말고 완전한 분석 코드'를 내도록 안내하는지 확인.

    스키마와 무관한 기본 지시이므로 schema=None(기본 워크플로)에서 검증한다.
    문구는 _BASE_PROMPT의 실제 출력과 일치시켜, 프롬프트가 약화되면 깨지게 한다.
    """
    p = build_system_prompt(connection_engine="postgres", schema=None)
    low = p.lower()
    # 작업 폴더 파일 목록(이름만)을 활용하라는 안내가 있어야 한다.
    assert "data files" in low
    # 사용자에게 "실행해서 결과를 붙여 달라"고 떠넘기지 말라는 지시.
    assert "paste the output back" in low
    # 컬럼을 모르면 코드 안에서 점검(inspect)하라는 지시.
    assert "inspect" in low
    # 시각화는 선택(요청 시에만)이라는 안내.
    assert "optional" in low


def test_renders_tables_and_pii_marker() -> None:
    schema = {
        "tables": [
            {
                "schema": "sales",
                "name": "customers",
                "columns": [
                    {"name": "id", "type": "integer", "pii_kind": None},
                    {"name": "email", "type": "text", "pii_kind": "email"},
                ],
            }
        ]
    }
    p = build_system_prompt(connection_engine="postgres", schema=schema)
    assert "sales.customers" in p
    assert "id:integer" in p
    assert "email:text [PII]" in p


def test_excludes_row_data() -> None:
    """안전성 점검: 프롬프트 빌더는 행(row) 값이 새어 들어가게 두지 않는다."""
    schema = {
        "tables": [
            {
                "schema": "sales",
                "name": "customers",
                "columns": [
                    {"name": "name", "type": "text", "pii_kind": "name"},
                ],
                # 호출자가 실수로 행 데이터를 붙였더라도 프롬프트에 나타나선 안 된다
                "rows": [{"name": "leaked@example.com"}],
            }
        ]
    }
    p = build_system_prompt(connection_engine="postgres", schema=schema)
    assert "leaked@example.com" not in p
