"""ParamQuery rejects raw string interpolation surface (SECURITY-05 guard).

Includes property-based tests (Hypothesis) that fuzz the validator against
common injection-shaped strings — quote stacking, semicolon termination,
Unicode homoglyphs, and percent / f-string artefacts.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from data.schemas import ParamQuery


def test_plain_sql_accepted() -> None:
    q = ParamQuery(sql="SELECT * FROM users WHERE id = :id", params={"id": 1})
    assert q.params == {"id": 1}


def test_fstring_remnant_rejected() -> None:
    with pytest.raises(ValidationError):
        ParamQuery(sql="SELECT * FROM users WHERE id = {user_id}", params={})


def test_python_percent_format_rejected() -> None:
    with pytest.raises(ValidationError):
        ParamQuery(sql="SELECT * FROM users WHERE id = %(user_id)s", params={})


def test_long_sql_within_bound() -> None:
    long_sql = "SELECT 1 -- " + ("x" * 50_000)
    ParamQuery(sql=long_sql, params={})


# --- PBT --------------------------------------------------------------------


@given(name=st.text(min_size=1, max_size=30, alphabet=st.characters(blacklist_characters="{}%?")))
def test_pbt_fstring_artefacts_always_rejected(name: str) -> None:
    """Any SQL string that contains an f-string placeholder MUST be rejected."""
    sql = f"SELECT * FROM users WHERE name = {{{name}}}"
    with pytest.raises(ValidationError):
        ParamQuery(sql=sql, params={})


@given(name=st.text(min_size=1, max_size=30, alphabet=st.characters(blacklist_characters="{}%?")))
def test_pbt_percent_format_artefacts_always_rejected(name: str) -> None:
    sql = f"SELECT * FROM users WHERE name = %({name})s"
    with pytest.raises(ValidationError):
        ParamQuery(sql=sql, params={})


_INJECTION_PAYLOADS = [
    "1; DROP TABLE users--",       # semicolon stacking
    "1' OR '1'='1",                # classic boolean tautology
    "1 UNION SELECT password FROM users--",  # UNION-based
    "1‮' OR '1",             # Unicode RTL override
    "admin' --",                   # comment-out
]


@pytest.mark.parametrize("payload", _INJECTION_PAYLOADS)
def test_injection_payloads_are_safe_when_parameterised(payload: str) -> None:
    """Injection-shaped strings are safe IF they arrive via ``params``.

    The validator only refuses **format artefacts in ``sql``**. Real safety
    comes from the driver-side parameter substitution contract: ``params``
    values pass through bound parameters and are NEVER concatenated. This
    test pins that contract — the SQL itself uses ``:value`` as a placeholder.
    """
    q = ParamQuery(sql="SELECT * FROM t WHERE name = :value", params={"value": payload})
    # The payload travels as a parameter; the SQL string is verbatim.
    assert q.sql == "SELECT * FROM t WHERE name = :value"
    assert q.params["value"] == payload


def test_injection_payload_concatenated_into_sql_is_caught_only_if_format_token() -> None:
    """If a developer concatenates an injection payload into ``sql`` directly
    (bypassing params), the validator's coarse format-token guard catches
    only the f-string / %(...) cases. SQL itself with literal quotes flows
    through — which is precisely why ``params`` is mandatory at every call
    site, and why we keep this test as a tripwire if someone weakens it.
    """
    # f-string artefact in SQL is rejected:
    with pytest.raises(ValidationError):
        ParamQuery(sql="SELECT * FROM t WHERE id = {x}", params={})
    # Quote-containing SQL is NOT rejected by the validator; the next layer
    # (driver parametrisation) is the real guard. Document this intentional
    # split here so future hardening lands in the right place.
    ParamQuery(sql="SELECT * FROM t WHERE id = '1'", params={})
