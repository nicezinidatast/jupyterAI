"""credential-unit 공개 API — 목록 조회 전용. 등록/삭제/로테이션은 admin-unit을 통한다.

설계 의도: credential-unit 자체 API는 읽기(read) 전용으로 제한해 권한 분리(separation of
duty)를 유지한다. 시크릿 값(평문)은 이 라우터에서 절대 반환하지 않는다 — vault_path만 노출한다.
"""

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
    """삭제되지 않은 Credential 목록을 등록 시각 순으로 반환한다.

    보안 주의: vault_path는 Vault/KMS 내부 경로를 노출하지만 시크릿 평문은 포함하지 않는다.
    이 엔드포인트를 통해 평문 시크릿에 접근하는 것은 불가능하다.
    """
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
