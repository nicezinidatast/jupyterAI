"""audit-unit 공개 API — 감사 로그 검색 + CSV 내보내기 (AuditorConsole용).

엔드포인트:
  GET /api/audit          — 필터·페이지네이션 지원 검색
  GET /api/audit/export.csv — 최대 10,000건 CSV 스트리밍 다운로드
  GET /api/audit/event-types — 존재하는 이벤트 타입 목록 (필터 UI용)

모든 엔드포인트는 읽기 전용이다. audit_log는 DB 트리거로 수정이 차단되어 있다.
"""

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
    """audit_log를 최신순으로 검색한다.

    resource 필터는 LIKE '%값%' 부분 일치를 사용한다 — 정확한 경로보다
    리소스 종류로 필터링하는 경우가 많기 때문이다.
    limit 상한은 500으로 제한해 과도한 DB 부하를 방지한다.
    """
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
    """audit_log를 CSV 파일로 스트리밍 다운로드한다.

    최대 10,000건으로 제한해 메모리 사용량을 통제한다.
    payload는 JSON 직렬화 문자열로 포함되므로 스프레드시트에서 열면 한 셀에 들어간다.
    StreamingResponse + iter([...]) 조합: 단건 버퍼를 스트리밍처럼 감싸는 간단한 패턴이다.
    """
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
        # payload가 문자열(SQLite TEXT 폴백)인 경우 dict로 파싱한다.
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
    """audit_log에 존재하는 이벤트 타입 목록을 정렬해서 반환한다.

    AuditorConsole의 필터 드롭다운 UI를 위해 제공된다.
    """
    rows = (
        await session.execute(select(AuditLog.event_type).distinct())
    ).scalars().all()
    return sorted(rows)


def _serialize(row: AuditLog) -> dict[str, Any]:
    """AuditLog ORM 객체를 API 응답용 dict로 변환한다.

    payload가 문자열로 저장된 경우(SQLite 폴백 또는 구 데이터) dict로 파싱을 시도하며,
    파싱 실패 시에는 {"raw": 원본_문자열} 형태로 감싸 API 응답이 항상 dict가 되도록 한다.
    """
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
