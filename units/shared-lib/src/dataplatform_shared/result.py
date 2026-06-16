"""Result / Either type for domain code (Q-AD-5=A).

Every domain function should return `Result[T, E]` rather than raising for
expected outcomes. System-level failures (OOM, disk full) may still raise; a
fail-closed global handler turns those into generalised messages.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Successful result holding a value."""

    value: T

    @property
    def ok(self) -> bool:  # noqa: D401 — short, simple property
        return True


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Failed result holding an error."""

    error: E

    @property
    def ok(self) -> bool:
        return False


# A Result is either an Ok carrying a value, or an Err carrying an error.
Result: TypeAlias = Ok[T] | Err[E]


def map_ok(result: Result[T, E], fn: Callable[[T], U]) -> Result[U, E]:
    """Transform the Ok value if present; leave Err untouched."""
    if isinstance(result, Ok):
        return Ok(fn(result.value))
    return result


def and_then(result: Result[T, E], fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
    """Chain a Result-returning function on Ok; short-circuit on Err."""
    if isinstance(result, Ok):
        return fn(result.value)
    return result


def unwrap(result: Result[T, E]) -> T:
    """Return the Ok value or raise ``ValueError`` if Err.

    Intended for test code or boundaries that must hard-fail.
    """
    if isinstance(result, Ok):
        return result.value
    raise ValueError(f"unwrap on Err: {result.error!r}")


def is_ok(result: Result[T, E]) -> bool:
    return isinstance(result, Ok)


def is_err(result: Result[T, E]) -> bool:
    return isinstance(result, Err)
