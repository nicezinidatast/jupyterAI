"""표준 도메인 에러 + fail-closed 경계 헬퍼 (SECURITY-15).

fail-closed(실패 시 안전 차단) 원칙: 예상 못 한 예외가 사용자에게 그대로
새어 나가면 스택 트레이스·내부 구조가 노출될 수 있으므로, 경계에서 모두
일반화된 에러로 덮는다.

- 도메인 에러는 예외가 아니라 ``Result[T, DomainError]``로 반환한다(result.py 참조).
- ``safe_boundary``를 빠져나가는 예상 밖 예외는 unit + op 태그와 함께 error
  레벨로 로깅하고, ``InternalError``로 다시 던진다. 그러면 전역 핸들러가
  스택 트레이스 노출 없이 일반적인 사용자 메시지로 변환할 수 있다.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator
from enum import Enum

logger = logging.getLogger(__name__)


class DomainError(str, Enum):
    """모든 단위에서 공유하는 도메인 수준 에러 코드.

    ``str``과 ``Enum``을 동시에 상속해 enum 멤버를 문자열처럼 직렬화·비교할 수
    있게 했다. 값은 클라이언트에 노출해도 안전한 안정적 식별자다 — 한번 정해지면
    바뀌지 않으므로 API 계약(contract)으로 의존해도 된다.
    """

    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION = "VALIDATION"
    EXTERNAL_UNAVAILABLE = "EXTERNAL_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    EXPIRED = "EXPIRED"
    BAD_INPUT = "BAD_INPUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class InternalError(Exception):
    """감싼 예상 밖 예외. 원본 정보 없이 일반화된 메시지만 운반한다.

    원래 예외의 상세는 의도적으로 버린다(``from None``으로 체이닝 차단) —
    내부 구현·민감 정보가 사용자에게 새지 않게 하기 위함.
    """

    code: str = DomainError.INTERNAL_ERROR.value

    def __init__(self, message: str = "internal_error") -> None:
        super().__init__(message)


class DomainException(Exception):
    """HTTP 경계에서 DomainError를 응답으로 변환하기 위해 던지는 예외.

    도메인 코드 내부에서는 예외 대신 ``Result``를 우선 쓴다. 이 예외는 오로지
    HTTP 핸들러가 적절한 상태 코드를 만들 수 있도록 경계에서만 사용한다.
    """

    def __init__(self, code: DomainError, *, http_status: int = 500, detail: str | None = None) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = detail
        super().__init__(code.value)


@contextlib.contextmanager
def safe_boundary(unit: str, op: str) -> Iterator[None]:
    """블록을 감싸 예상 밖 예외를 ``InternalError``로 바꾸는 컨텍스트 매니저.

    except 순서가 중요하다:
    - ``DomainException``: 의도적으로 그대로 통과시킨다. HTTP 핸들러가 적절한
      상태 코드를 렌더링해야 하므로 일반화하면 안 된다.
    - ``InternalError``: 이미 일반화된 것이라 그대로 다시 던진다(이중 래핑 방지).
    - 그 외 모든 예외: 구조화된 컨텍스트(unit·op)와 함께 로깅한 뒤,
      ``from None``으로 원본 체인을 끊고 일반 ``InternalError``로 다시 던진다.
      원본 예외 정보가 사용자에게 새지 않게 하기 위함이다.
    """

    try:
        yield
    except DomainException:
        raise
    except InternalError:
        raise
    except Exception:
        logger.exception("safe_boundary captured unexpected error", extra={"unit": unit, "op": op})
        raise InternalError() from None
