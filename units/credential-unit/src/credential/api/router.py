"""credential-unit public API — list only. Mutations go through admin-unit."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from credential.models import Credential

router = APIRouter(prefix="/api/credentials", tags=["credentials"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("")
async def list_credentials(session: Session) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(Credential).where(Credential.deleted_at.is_(None)).order_by(Credential.created_at)
        )
    ).scalars().all()
    return [
        {
            "credential_id": str(c.credential_id),
            "scope": c.scope,
            "name": c.name,
            "vault_path": c.vault_path,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "rotated_at": c.rotated_at.isoformat() if c.rotated_at else None,
        }
        for c in rows
    ]
