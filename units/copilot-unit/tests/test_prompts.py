"""build_system_prompt — schema injection, no PII data, table rendering."""

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
    """Sanity: the prompt builder never lets row values sneak in."""
    schema = {
        "tables": [
            {
                "schema": "sales",
                "name": "customers",
                "columns": [
                    {"name": "name", "type": "text", "pii_kind": "name"},
                ],
                # Even if a caller mistakenly attached row data, it must not appear
                "rows": [{"name": "leaked@example.com"}],
            }
        ]
    }
    p = build_system_prompt(connection_engine="postgres", schema=schema)
    assert "leaked@example.com" not in p
