"""build_system_prompt 테스트 — 스키마 주입, PII 데이터 미포함, 테이블 렌더링."""

from __future__ import annotations

from copilot.prompts import build_system_prompt


def test_no_schema() -> None:
    p = build_system_prompt(connection_engine="postgres", schema=None)
    assert "No schema attached" in p
    assert "postgres" in p


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
