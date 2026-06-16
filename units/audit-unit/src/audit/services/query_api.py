"""Search + export over audit_log (used by AuditorConsole)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Ok, Result

from audit.models import AuditLog


@dataclass(frozen=True, slots=True)
class AuditFilter:
    actor_id: str | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None
    event_types: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()


class AuditQueryApi:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self, filt: AuditFilter, *, page: int = 0, page_size: int = 100
    ) -> Result[list[dict], DomainError]:
        stmt = select(AuditLog)
        if filt.actor_id:
            stmt = stmt.where(AuditLog.actor_id == filt.actor_id)
        if filt.from_at:
            stmt = stmt.where(AuditLog.occurred_at >= filt.from_at)
        if filt.to_at:
            stmt = stmt.where(AuditLog.occurred_at <= filt.to_at)
        if filt.event_types:
            stmt = stmt.where(AuditLog.event_type.in_(filt.event_types))
        if filt.resources:
            stmt = stmt.where(AuditLog.resource.in_(filt.resources))
        stmt = stmt.order_by(AuditLog.occurred_at.desc()).limit(page_size).offset(page * page_size)
        rows = (await self._session.execute(stmt)).scalars().all()
        return Ok([self._serialize(r) for r in rows])

    @staticmethod
    def _serialize(row: AuditLog) -> dict:
        return {
            "id": row.id,
            "event_type": row.event_type,
            "actor_id": row.actor_id,
            "resource": row.resource,
            "result": row.result,
            "occurred_at": row.occurred_at.isoformat(),
            "corr_id": row.corr_id,
            "payload": row.payload,
        }
