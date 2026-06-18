"""PII(개인식별정보) 마스킹 + 안전한 정규식 검증.

마스킹 알고리즘은 의도적으로 멱등(idempotent)하게 설계했다. ``apply_mask``를
두 번 적용해도 결과가 같다. 덕분에 오라클(oracle)을 기준으로 PBT(속성 기반
테스트)를 돌릴 수 있다 — "마스킹된 문자열에는 원본 문자열이 절대 들어있지
않다"는 불변식을 깨지 않는 한 안전하다. 멱등성이 깨지면 이미 가린 값을 다시
가려 정보가 더 사라지거나, 거꾸로 마스킹이 풀릴 위험이 생긴다.

정규식은 표준 ``re`` 대신 third-party ``regex``를 쓴다. 매치 단위 타임아웃을
지원해, 악의적 입력으로 인한 ReDoS(정규식 서비스 거부, 파국적 백트래킹)를
시간 제한으로 차단할 수 있기 때문이다.
"""

from __future__ import annotations

import re as stdlib_re
from typing import Any

import regex  # third-party — 매치 단위 타임아웃 지원(ReDoS 방어용)

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result

# PII 종류별 탐지 정규식. RRN=주민등록번호(Resident Registration Number).
# 한글 이름·RRN·휴대전화·이메일을 한국 형식에 맞춰 식별한다.
PATTERNS: dict[str, regex.Pattern[str]] = {
    "name": regex.compile(r"^[가-힣]{2,4}$"),
    "rrn": regex.compile(r"\b\d{6}-?\d{7}\b"),
    "phone": regex.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
    "email": regex.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
}

# ``apply_mask``가 만들어내는, 다시 마스킹하면 안 되는 토큰 표식.
_MASK_TOKENS = ("*",)


def apply_mask(value: str, kind: str) -> str:
    """PII 종류에 맞춰 단일 값 하나를 마스킹한다.

    우리가 쓰는 마스킹 형태에 대해 멱등하다. 다시 적용해도 출력이 덜 가려지는
    일은 없으며, 같은 출력으로 수렴한다(이미 '900101-*******'인 값을 다시
    rrn으로 마스킹해도 앞 6자리를 그대로 보존하므로 결과가 유지된다).
    """
    if not isinstance(value, str):
        return value
    if kind == "name":
        # 한국 이름 관례: 2자는 끝 글자만, 3자 이상은 가운데만 가린다.
        # 한 글자(성만 있음)는 더 가릴 게 없어 원본을 그대로 둔다.
        if len(value) < 2:
            return value
        if len(value) == 2:
            return value[0] + "*"
        return value[0] + ("*" * (len(value) - 2)) + value[-1]
    if kind == "rrn":
        # 앞 6자리(생년월일)만 남기고 나머지를 가린다. 기존 하이픈을 먼저
        # 제거해, 하이픈 유무와 무관하게 같은 결과를 내도록(멱등성 보장).
        compact = value.replace("-", "")
        return compact[:6] + "-*******"
    if kind == "phone":
        # 하이픈을 떼고 자릿수로 판단. 국번 3자리와 끝 4자리만 남긴다.
        # 10자리 미만이면 정상 휴대전화가 아니므로 손대지 않는다.
        compact = value.replace("-", "")
        if len(compact) < 10:
            return value
        return f"{compact[:3]}-****-{compact[-4:]}"
    if kind == "email":
        # 로컬 파트 첫 글자만 남기고 도메인은 보존(분류·집계에 도메인은 유용).
        # '@'가 없거나 로컬 파트가 비면 이메일이 아니므로 원본 유지.
        user, sep, domain = value.partition("@")
        if not sep or not user:
            return value
        return user[0] + "***@" + domain
    # 알 수 없는 종류는 안전하게 전부 가린다(누설보다 과한 마스킹이 낫다).
    return "***"


def detect_kind(value: str) -> str | None:
    """정규식이 매치되는 첫 PII 종류를 반환, 없으면 None.

    각 search에 timeout=0.1을 걸어, 악의적·병적 입력이 정규식 엔진을 오래
    붙잡는 ReDoS를 막는다. 타임아웃이 나면 그 종류는 건너뛰고 다음으로 넘어간다
    (전체 탐지를 멈추지 않기 위함).
    """
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
    """행을 컬럼 단위로 마스킹한다. 종류가 지정되지 않은 컬럼은 자동 탐지한다.

    ``column_kinds``로 명시된 종류를 우선 적용하고, None이면 값으로부터
    ``detect_kind``로 추정한다. 그래도 None이면 PII가 아니라고 보고 원본을
    그대로 둔다 — 즉 "명시 종류 > 자동 탐지 > 원본 유지" 순으로 결정한다.
    """
    masked: dict[str, Any] = {}
    for col, val in row.items():
        kind = column_kinds.get(col) or (detect_kind(val) if isinstance(val, str) else None)
        if kind is None:
            masked[col] = val
        else:
            masked[col] = apply_mask(val, kind)
    return masked


def validate_regex(pattern: str) -> Result[None, DomainError]:
    """저장 전에 명백히 위험한 정규식 패턴을 거절한다(ReDoS 1차 방어).

    관리자가 등록하는 커스텀 PII 패턴이 파국적 백트래킹을 유발하면 운영 중
    탐지 호출 전체를 마비시킬 수 있다. 그래서 영속화 이전에 세 겹으로 막는다:
    1) 길이 상한(256)으로 과도하게 긴 패턴 차단,
    2) 중첩 수량자(``(.*)*`` 등) 같은 대표적 위험 형태를 문자열로 선검출,
    3) 컴파일 후 짧은 입력에 timeout=0.05로 스모크 실행해 실제 폭주를 잡는다.
    """
    if not pattern or len(pattern) > 256:
        return Err(DomainError.VALIDATION)
    # 중첩 수량자는 입력 길이에 지수적으로 폭주하는 전형적 ReDoS 형태다.
    if any(bad in pattern for bad in ("(.*)*", "(.+)+", "(.+)*", "(.*)+")):
        return Err(DomainError.VALIDATION)
    try:
        compiled = regex.compile(pattern)
        # 짧은 입력에 타임아웃을 걸어 스모크 실행 — 파국적 백트래킹을 사전에 포착.
        compiled.fullmatch("test", timeout=0.05)
    except (regex.error, TimeoutError, stdlib_re.error):
        # 컴파일 오류·타임아웃 모두 "쓰면 안 될 패턴"이므로 동일하게 거절한다.
        return Err(DomainError.VALIDATION)
    return Ok(None)
