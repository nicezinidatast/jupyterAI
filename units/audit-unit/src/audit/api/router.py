"""audit-unit public API — search + CSV export for the Auditor console."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit.models import AuditLog
from backend.db import get_session

router = APIRouter(prefix="/api/audit", tags=["audit"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("")
async def search(
    session: Session,
    actor: str | None = None,
    event_type: str | None = None,
    resource: str | None = None,
    result: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    stmt = select(AuditLog)
    if actor:
        stmt = stmt.where(AuditLog.actor_id == actor)
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if resource:
        stmt = stmt.where(AuditLog.resource.like(f"%{resource}%"))
    if result:
        stmt = stmt.where(AuditLog.result == result)
    stmt = stmt.order_by(AuditLog.occurred_at.desc()).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()
    return {
        "items": [_serialize(r) for r in rows],
        "count": len(rows),
        "offset": offset,
        "limit": limit,
    }


@router.get("/export.csv")
async def export_csv(
    session: Session,
    actor: str | None = None,
    event_type: str | None = None,
    resource: str | None = None,
    result: str | None = None,
) -> StreamingResponse:
    stmt = select(AuditLog)
    if actor:
        stmt = stmt.where(AuditLog.actor_id == actor)
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if resource:
        stmt = stmt.where(AuditLog.resource.like(f"%{resource}%"))
    if result:
        stmt = stmt.where(AuditLog.result == result)
    stmt = stmt.order_by(AuditLog.occurred_at.desc()).limit(10_000)
    rows = (await session.execute(stmt)).scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["id", "occurred_at", "event_type", "actor", "resource", "result", "corr_id", "payload"]
    )
    for r in rows:
        payload = r.payload if isinstance(r.payload, dict) else (
            json.loads(r.payload) if r.payload else {}
        )
        writer.writerow(
            [
                r.id,
                r.occurred_at.isoformat() if r.occurred_at else "",
                r.event_type,
                r.actor_id or "",
                r.resource or "",
                r.result,
                r.corr_id or "",
                json.dumps(payload, ensure_ascii=False),
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit-log.csv"'},
    )


@router.get("/event-types")
async def event_types(session: Session) -> list[str]:
    rows = (
        await session.execute(select(AuditLog.event_type).distinct())
    ).scalars().all()
    return sorted(rows)


def _serialize(row: AuditLog) -> dict[str, Any]:
    payload = row.payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"raw": payload}
    return {
        "id": row.id,
        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        "event_type": row.event_type,
        "actor_id": row.actor_id,
        "resource": row.resource,
        "result": row.result,
        "corr_id": row.corr_id,
        "payload": payload,
    }
