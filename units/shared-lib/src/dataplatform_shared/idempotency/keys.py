"""결정적 멱등성 키 생성기.

이 함수는 반드시 순수(pure)해야 한다: 같은 입력이면 언제나 같은 키가 나와야
한다(시간·난수 등 외부 상태 의존 금지). 그래야 클라이언트가 재시도해도 서버가
같은 키로 중복을 식별해 한 번만 처리한다. data-unit(credential 등록),
notebook-unit(노트북 저장) 등에서 쓰인다.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def idempotency_key(user_id: str, operation: str, resource: Any) -> str:
    """안정적인 ``user:op:hash16`` 식별자를 반환한다.

    순수성을 위해 직렬화 옵션이 중요하다: ``sort_keys=True``로 dict의 키를
    정렬해, 삽입 순서만 다른 같은 내용의 dict가 동일한 키를 만들게 한다.
    ``default=str``는 직렬화 불가 타입을 문자열로 강제해 예외 대신 안정적
    표현을 얻고, ``separators``는 공백을 없애 표현을 정규화한다. 해시는
    sha256 앞 16자리만 써 키 길이를 제한하되 충돌 확률은 실무상 무시 가능하다.
    """
    encoded = json.dumps(resource, sort_keys=True, default=str, separators=(",", ":")).encode()
    digest = hashlib.sha256(encoded).hexdigest()[:16]
    return f"{user_id}:{operation}:{digest}"
