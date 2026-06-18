"""분석가용 코파일럿의 시스템 프롬프트 빌더.

FR-LLM-05에 따라, 프롬프트에는 **메타데이터**(테이블·컬럼 이름과 타입)만 담고
실제 행(row) 값은 절대 넣지 않는다. 행을 요약하고 싶은 호출자는 클라이언트
쪽에서 처리하거나, 별도의 감사되는(audited) "row-summary" 엔드포인트를 써야 한다.

주의: 아래 ``_BASE_PROMPT`` 등 프롬프트 문자열은 LLM 동작에 직결되는 기능성
데이터이므로 번역·수정하지 않는다(원문 영어 그대로 유지).
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
    """기본 프롬프트 뒤에 스키마를 덧붙여 시스템 프롬프트를 조립한다.

    ``schema``는 ``GET /api/connections/{id}/schema``의 응답으로, ``tables``
    리스트를 담은 dict다. 사용자가 아직 연결(connection)을 고르지 않았으면
    ``None``을 넘긴다 — 이 경우 DB 없이 파일 기반 워크플로용 안내를 덧붙인다.
    """
    parts = [_BASE_PROMPT.strip(), f"Active engine: {connection_engine or 'unknown'}"]
    if schema:
        parts.append("\nSCHEMA")
        for t in schema.get("tables", []):
            # 스키마명이 있으면 "schema.table"로 한정(qualify)하고, 없으면 테이블명만.
            qualified = f"{t.get('schema')}.{t['name']}" if t.get("schema") else t["name"]
            # 컬럼은 "이름:타입" 형식. PII로 분류된 컬럼엔 [PII] 표식을 붙여
            # 모델이 그 컬럼 값을 에코하지 않도록 신호를 준다(값 자체는 미포함).
            cols = ", ".join(
                f"{c['name']}:{c['type']}{' [PII]' if c.get('pii_kind') else ''}"
                for c in t.get("columns", [])
            )
            parts.append(f"- {qualified}({cols})")
    else:
        parts.append(
            "\nNo database is attached (this is an internal, file-based workflow). "
            "Analysts upload data files (CSV/TSV/JSON/Parquet/Excel) into the "
            "JupyterLab workspace and read them from ~/work/. Help them load and "
            "analyze those files with pandas/numpy/matplotlib and answer Python "
            "questions. Do NOT ask for a database connection."
        )
    return "\n".join(parts)
