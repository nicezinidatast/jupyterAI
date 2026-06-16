"""Public DTOs. ``ParamQuery`` is the canonical container that forbids string
interpolation: callers MUST pass placeholders + a params dict."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Reject anything that looks like raw f-string interpolation. This is a coarse
# guard — the actual SQL driver enforces real parameter substitution.
_DISALLOWED_PATTERNS = (
    re.compile(r"\{[^}]+\}"),       # f-string remnants
    re.compile(r"%\([^)]+\)s"),     # python % formatting (only %s allowed via driver)
    re.compile(r"\?\s*\|\|\s*"),    # naive concatenation
)


class ParamQuery(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    sql: str = Field(min_length=1, max_length=100_000)
    params: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @field_validator("sql")
    @classmethod
    def reject_format_artifacts(cls, v: str) -> str:
        for pattern in _DISALLOWED_PATTERNS:
            if pattern.search(v):
                raise ValueError("sql contains string-formatting artifacts")
        return v


class ConnectionSpec(BaseModel):
    name: str
    engine: str
    host: str
    port: int
    database: str | None = None
    credential_id: str  # UUID
    options: dict[str, Any] = Field(default_factory=dict)
