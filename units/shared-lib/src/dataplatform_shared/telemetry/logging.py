"""Structured JSON logging via structlog (NFR-SL-OBS-02 / NFR-SEC-03).

The correlation id lives in a ``ContextVar`` so async tasks inherit it, and
``_inject_corr_id`` automatically attaches it to every log line.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

import structlog

_corr_id_var: ContextVar[str | None] = ContextVar("corr_id", default=None)


def _inject_corr_id(
    _logger: Any, _name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    cid = _corr_id_var.get()
    if cid is not None:
        event_dict.setdefault("corr_id", cid)
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Idempotent — safe to call multiple times in tests."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _inject_corr_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(_level_to_int(level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _level_to_int(level: str) -> int:
    import logging

    return logging.getLevelNamesMapping().get(level.upper(), logging.INFO)


def bind_corr_id(corr_id: str) -> None:
    """Bind a correlation id to the current async / thread context."""
    _corr_id_var.set(corr_id)


def get_corr_id() -> str | None:
    return _corr_id_var.get()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
