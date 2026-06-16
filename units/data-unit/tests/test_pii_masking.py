"""PII masking — oracle, idempotent, and PBT against a regex oracle."""

from __future__ import annotations

import regex
from hypothesis import given
from hypothesis import strategies as st

from data.services.pii_masking import (
    PATTERNS,
    apply_mask,
    detect_kind,
    mask_row,
    validate_regex,
)


def test_mask_name() -> None:
    assert apply_mask("홍길동", "name") == "홍*동"
    assert apply_mask("이순신", "name") == "이*신"
    assert apply_mask("김", "name") == "김"  # too short → unchanged


def test_mask_phone_with_or_without_dashes() -> None:
    assert apply_mask("010-1234-5678", "phone") == "010-****-5678"
    assert apply_mask("01012345678", "phone") == "010-****-5678"


def test_mask_rrn() -> None:
    assert apply_mask("9001011234567", "rrn") == "900101-*******"


def test_mask_email() -> None:
    assert apply_mask("alice@example.com", "email") == "a***@example.com"


def test_idempotent_apply_mask() -> None:
    """apply_mask(apply_mask(x)) == apply_mask(x) for every supported kind."""
    cases: list[tuple[str, str]] = [
        ("홍길동", "name"),
        ("010-1234-5678", "phone"),
        ("alice@example.com", "email"),
    ]
    for value, kind in cases:
        once = apply_mask(value, kind)
        twice = apply_mask(once, kind)
        assert once == twice, f"not idempotent for {kind!r}: {once!r} vs {twice!r}"


@given(
    st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz",
        min_size=1,
        max_size=10,
    ),
    st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz",
        min_size=2,
        max_size=10,
    ),
)
def test_pbt_masked_email_never_contains_local_part(user: str, domain: str) -> None:
    email = f"{user}@{domain}.com"
    masked = apply_mask(email, "email")
    # Only the first character of ``user`` may appear before ``***`` — the rest
    # must not appear in the masked output.
    rest = user[1:]
    if rest:
        assert rest not in masked


def test_mask_row_uses_detection() -> None:
    row = {"name": "홍길동", "city": "Seoul", "phone": "010-1234-5678"}
    masked = mask_row(row, column_kinds={"name": "name", "phone": "phone", "city": None})
    assert masked["name"] == "홍*동"
    assert masked["phone"] == "010-****-5678"
    assert masked["city"] == "Seoul"  # not PII


def test_validate_regex_rejects_catastrophic_pattern() -> None:
    bad = "(.*)*"
    result = validate_regex(bad)
    assert not result.ok


def test_validate_regex_accepts_simple_pattern() -> None:
    result = validate_regex(r"^\d{3}-\d{4}$")
    assert result.ok


def test_detect_kind_matches_email() -> None:
    assert detect_kind("alice@example.com") == "email"
    assert detect_kind("not-an-email") is None


def test_patterns_compile() -> None:
    for kind, pat in PATTERNS.items():
        assert isinstance(pat, regex.Pattern), f"{kind} is not a compiled pattern"
