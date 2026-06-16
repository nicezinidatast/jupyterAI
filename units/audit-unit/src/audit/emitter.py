"""Default emitter implementation — drops events into the outbox table."""

from __future__ import annotations

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.audit.events import DomainEvent

from audit.models import AuditOutbox


class OutboxAuditEmitter:
    """Implements the ``AuditEventEmitter`` Protocol from shared-lib.

    The emitter never opens its own transaction — the caller's session decides
    when to commit, which keeps the audit row atomic with the domain change.
    """

    async def emit(self, session: AsyncSession, event: DomainEvent) -> None:
        await session.execute(insert(AuditOutbox).values(event=event))
