"""System prompt builder for the analyst copilot.

Per FR-LLM-05, only **metadata** (table + column names + types) is included in
the prompt — never row values. Callers that want to summarise rows must do so
client-side or via a separate, audited "row-summary" endpoint.
"""

from __future__ import annotations

from typing import Any

_BASE_PROMPT = """\
You are an internal data-analytics assistant embedded inside a JupyterLab
workspace. Help analysts answer business questions by writing safe,
parameterised SQL or pandas/numpy/matplotlib snippets.

Hard rules:
1. Generate SQL that uses ONLY the tables and columns listed in the SCHEMA
   block. If the user's question can't be answered with that schema, say so.
2. When the user asks for a "chart" or "graph", produce both the SQL and a
   short pandas/plotly snippet that consumes the result DataFrame.
3. Always wrap code in fenced blocks with the right language tag: ```sql,
   ```python.
4. Never echo back PII column values. The platform masks them, but you should
   not invent or paraphrase them either.
5. Keep responses concise — analysts want the code, then a 1-2 sentence
   explanation.
"""


def build_system_prompt(
    *,
    connection_engine: str,
    schema: dict[str, Any] | None,
) -> str:
    """Assemble the system prompt with the schema appended.

    ``schema`` is the response from ``GET /api/connections/{id}/schema`` —
    a dict with a ``tables`` list. Pass ``None`` when the user hasn't picked
    a connection yet.
    """
    parts = [_BASE_PROMPT.strip(), f"Active engine: {connection_engine or 'unknown'}"]
    if schema:
        parts.append("\nSCHEMA")
        for t in schema.get("tables", []):
            qualified = f"{t.get('schema')}.{t['name']}" if t.get("schema") else t["name"]
            cols = ", ".join(
                f"{c['name']}:{c['type']}{' [PII]' if c.get('pii_kind') else ''}"
                for c in t.get("columns", [])
            )
            parts.append(f"- {qualified}({cols})")
    else:
        parts.append(
            "\nNo schema attached. Ask the user which connection they want to query "
            "before generating SQL."
        )
    return "\n".join(parts)
