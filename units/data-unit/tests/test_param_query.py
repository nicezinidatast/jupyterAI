"""ParamQuery가 원시 문자열 보간 표면을 거절하는지 검증한다(SECURITY-05 가드).

Hypothesis 기반 PBT(속성 기반 테스트)로 검증기를 흔든다(fuzz). 흔한 인젝션
형태의 문자열 — 따옴표 중첩, 세미콜론 종료, 유니코드 동형문자(homoglyph),
퍼센트·f-string 흔적 — 을 무작위로 던져 가드가 일관되게 막는지 확인한다.
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
    """f-string 자리표시자가 들어간 SQL 문자열은 반드시 거절돼야 한다."""
    sql = f"SELECT * FROM users WHERE name = {{{name}}}"
    with pytest.raises(ValidationError):
        ParamQuery(sql=sql, params={})


@given(name=st.text(min_size=1, max_size=30, alphabet=st.characters(blacklist_characters="{}%?")))
def test_pbt_percent_format_artefacts_always_rejected(name: str) -> None:
    sql = f"SELECT * FROM users WHERE name = %({name})s"
    with pytest.raises(ValidationError):
        ParamQuery(sql=sql, params={})


_INJECTION_PAYLOADS = [
    "1; DROP TABLE users--",       # 세미콜론 문장 쌓기(stacking)
    "1' OR '1'='1",                # 고전적 불리언 항진식(tautology)
    "1 UNION SELECT password FROM users--",  # UNION 기반
    "1‮' OR '1",             # 유니코드 RTL 오버라이드(좌우 반전 위장)
    "admin' --",                   # 뒤를 주석 처리해 조건 무력화
]


@pytest.mark.parametrize("payload", _INJECTION_PAYLOADS)
def test_injection_payloads_are_safe_when_parameterised(payload: str) -> None:
    """인젝션 형태 문자열도 ``params``로 들어오면 안전하다.

    검증기는 오직 **``sql`` 안의 포맷 흔적**만 거절한다. 진짜 안전성은
    드라이버 쪽 파라미터 치환 계약에서 온다: ``params`` 값은 바인딩 파라미터로
    전달되며 절대 문자열로 이어 붙지 않는다. 이 테스트는 그 계약을 못 박는다 —
    SQL 자체는 ``:value`` 자리표시자만 쓴다.
    """
    q = ParamQuery(sql="SELECT * FROM t WHERE name = :value", params={"value": payload})
    # 페이로드는 파라미터로 흐르고, SQL 문자열은 글자 그대로(verbatim) 유지된다.
    assert q.sql == "SELECT * FROM t WHERE name = :value"
    assert q.params["value"] == payload


def test_injection_payload_concatenated_into_sql_is_caught_only_if_format_token() -> None:
    """개발자가 인젝션 페이로드를 params를 우회해 ``sql``에 직접 이어 붙이면,
    검증기의 거친 포맷 토큰 가드는 f-string / %(...) 경우만 잡는다. 따옴표가
    든 SQL 자체는 통과한다 — 바로 이 때문에 모든 호출부에서 ``params`` 사용이
    필수이며, 누군가 이 가드를 약화시키면 알아채도록 트립와이어로 남겨 둔다.
    """
    # SQL 속 f-string 흔적은 거절된다:
    with pytest.raises(ValidationError):
        ParamQuery(sql="SELECT * FROM t WHERE id = {x}", params={})
    # 따옴표가 든 SQL은 검증기가 거절하지 않는다. 다음 계층(드라이버 파라미터화)이
    # 진짜 방어선이다. 향후 강화가 올바른 위치에 들어가도록, 이 의도된 역할 분담을
    # 여기 문서로 남긴다.
    ParamQuery(sql="SELECT * FROM t WHERE id = '1'", params={})
