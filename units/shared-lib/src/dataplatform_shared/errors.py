"""Standard domain errors + fail-closed boundary helper (SECURITY-15).

Domain errors are returned via ``Result[T, DomainError]``. Unexpected exceptions
escaping a ``safe_boundary`` are logged at error level with the unit + op tag and
re-raised as ``InternalError`` so the global handler can convert them into a
generic user-facing message without leaking stack traces.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator
from enum import Enum

logger = logging.getLogger(__name__)


class DomainError(str, Enum):
    """Domain-level error codes used across all units.

    Values are stable identifiers safe to expose to clients.
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
    """Wrapped unexpected exception. Carries a generalised message only."""

    code: str = DomainError.INTERNAL_ERROR.value

    def __init__(self, message: str = "internal_error") -> None:
        super().__init__(message)


class DomainException(Exception):
    """Used at HTTP boundaries to coerce a DomainError into a response.

    Domain code itself should prefer ``Result`` over raising.
    """

    def __init__(self, code: DomainError, *, http_status: int = 500, detail: str | None = None) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = detail
        super().__init__(code.value)


@contextlib.contextmanager
def safe_boundary(unit: str, op: str) -> Iterator[None]:
    """Wrap a block so unexpected exceptions become ``InternalError``.

    ``DomainException`` passes through unchanged so HTTP handlers can render
    proper status codes. Anything else is logged with structured context and
    re-raised as a generic ``InternalError``.
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
