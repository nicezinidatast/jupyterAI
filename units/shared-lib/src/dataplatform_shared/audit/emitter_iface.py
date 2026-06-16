"""Audit emitter Protocol — concrete impl in audit-unit (OutboxAuditEmitter)."""

from __future__ import annotations

from typing import Any, Protocol

from dataplatform_shared.audit.events import DomainEvent


class AuditEventEmitter(Protocol):
    """Implementations enqueue events into an outbox tied to the caller's DB tx.

    The first positional argument is intentionally typed ``Any`` so audit-unit's
    SQLAlchemy session and a test fake can both satisfy it without leaking a
    SQLAlchemy dependency into shared-lib.
    """

    async def emit(self, session: Any, event: DomainEvent) -> None: ...
