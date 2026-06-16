"""PII masking + safe regex validation.

The masking algorithm is intentionally idempotent: applying ``apply_mask``
twice yields the same output, which lets us PBT against an oracle (the masked
string never contains the source string).
"""

from __future__ import annotations

import re as stdlib_re
from typing import Any

import regex  # third-party — supports per-match timeouts

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result

PATTERNS: dict[str, regex.Pattern[str]] = {
    "name": regex.compile(r"^[가-힣]{2,4}$"),
    "rrn": regex.compile(r"\b\d{6}-?\d{7}\b"),
    "phone": regex.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
    "email": regex.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
}

# Strings produced by ``apply_mask`` that we never want to re-mask.
_MASK_TOKENS = ("*",)


def apply_mask(value: str, kind: str) -> str:
    """Mask a single value according to its PII kind.

    The function is idempotent for our masking shapes: re-applying never makes
    the output less masked.
    """
    if not isinstance(value, str):
        return value
    if kind == "name":
        if len(value) < 2:
            return value
        if len(value) == 2:
            return value[0] + "*"
        return value[0] + ("*" * (len(value) - 2)) + value[-1]
    if kind == "rrn":
        # Keep the first 6, mask the rest. Strip existing dashes for stability.
        compact = value.replace("-", "")
        return compact[:6] + "-*******"
    if kind == "phone":
        compact = value.replace("-", "")
        if len(compact) < 10:
            return value
        return f"{compact[:3]}-****-{compact[-4:]}"
    if kind == "email":
        user, sep, domain = value.partition("@")
        if not sep or not user:
            return value
        return user[0] + "***@" + domain
    return "***"


def detect_kind(value: str) -> str | None:
    """Return the first PII kind whose regex matches the value, else None."""
    if not isinstance(value, str):
        return None
    for kind, pattern in PATTERNS.items():
        try:
            if pattern.search(value, timeout=0.1):
                return kind
        except TimeoutError:
            continue
    return None


def mask_row(row: dict[str, Any], column_kinds: dict[str, str | None]) -> dict[str, Any]:
    """Apply masking column-by-column. Unknown columns are auto-detected."""
    masked: dict[str, Any] = {}
    for col, val in row.items():
        kind = column_kinds.get(col) or (detect_kind(val) if isinstance(val, str) else None)
        if kind is None:
            masked[col] = val
        else:
            masked[col] = apply_mask(val, kind)
    return masked


def validate_regex(pattern: str) -> Result[None, DomainError]:
    """Reject obviously dangerous patterns before persisting them."""
    if not pattern or len(pattern) > 256:
        return Err(DomainError.VALIDATION)
    if any(bad in pattern for bad in ("(.*)*", "(.+)+", "(.+)*", "(.*)+")):
        return Err(DomainError.VALIDATION)
    try:
        compiled = regex.compile(pattern)
        # Smoke run with a timeout to catch catastrophic backtracking on short input.
        compiled.fullmatch("test", timeout=0.05)
    except (regex.error, TimeoutError, stdlib_re.error):
        return Err(DomainError.VALIDATION)
    return Ok(None)
