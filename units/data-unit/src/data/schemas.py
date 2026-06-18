"""공개 DTO. ``ParamQuery``는 문자열 보간을 금지하는 표준 컨테이너다 —
호출부는 SQL에 값을 끼워 넣지 말고 반드시 자리표시자(placeholder)와 params
dict를 함께 넘겨야 한다. SQL 인젝션 방어의 1차 관문이며, 진짜 방어는 드라이버의
파라미터 바인딩이다(이 검증은 보조적인 거친 필터)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 원시 문자열 포매팅 흔적처럼 보이는 것을 거절한다. 이는 거친(coarse) 가드이며,
# 실제 파라미터 치환은 SQL 드라이버가 강제한다. 즉 "값을 SQL에 박아 넣는"
# 잘못된 호출 패턴을 조기에 잡아내는 트립와이어(tripwire) 역할이다.
_DISALLOWED_PATTERNS = (
    re.compile(r"\{[^}]+\}"),       # f-string 잔재 ({var})
    re.compile(r"%\([^)]+\)s"),     # 파이썬 % 포매팅 (드라이버 경유 %s만 허용)
    re.compile(r"\?\s*\|\|\s*"),    # 순진한 문자열 연결(concatenation)
)


class ParamQuery(BaseModel):
    # frozen: 생성 후 불변이라 검증을 통과한 쿼리가 도중에 변조되지 않는다.
    # str_strip_whitespace: 앞뒤 공백을 정리해 비교·검증을 안정화한다.
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    sql: str = Field(min_length=1, max_length=100_000)
    params: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @field_validator("sql")
    @classmethod
    def reject_format_artifacts(cls, v: str) -> str:
        # 금지 패턴 중 하나라도 걸리면 거절한다. 따옴표가 든 SQL 자체는 통과하며
        # (그건 드라이버 바인딩이 막는다), 여기서는 포맷 토큰 오용만 걸러낸다.
        for pattern in _DISALLOWED_PATTERNS:
            if pattern.search(v):
                raise ValueError("sql contains string-formatting artifacts")
        return v


class ConnectionSpec(BaseModel):
    # 커넥터를 만드는 데 필요한 접속 정보 묶음. 비밀번호는 여기 담지 않고
    # credential_id로 참조만 한다(비밀은 vault에서 별도 복호화).
    name: str
    engine: str
    host: str
    port: int
    database: str | None = None
    credential_id: str  # UUID 문자열
    options: dict[str, Any] = Field(default_factory=dict)
