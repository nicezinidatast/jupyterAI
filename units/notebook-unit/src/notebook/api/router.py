"""notebook-unit 공개 API — 워크스페이스, 노트북, 버전, 공유 링크.

REST 엔드포인트 계층으로, 실제 도메인 로직(멱등 저장·outbox 발신)은
NotebookService에 위임하고 여기서는 HTTP 입출력 변환만 담당한다.
공유 링크 조회/생성도 제공하지만, 권한 등급 비교 같은 핵심 불변식은
ShareLinkManager(서비스 계층)에 있다는 점에 유의한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from notebook.models import (
    Notebook,
    NotebookVersion,
    ShareAudience,
    ShareLink,
    Workspace,
)
from notebook.services.notebook_service import NotebookService

router = APIRouter(prefix="/api", tags=["notebook"])
Session = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------
class WorkspaceOut(BaseModel):
    workspace_id: UUID
    name: str
    kind: str
    git_repo_url: str
    git_branch: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/workspaces")
async def list_workspaces(session: Session) -> list[WorkspaceOut]:
    rows = (
        await session.execute(select(Workspace).order_by(Workspace.created_at))
    ).scalars().all()
    return [WorkspaceOut.model_validate(r) for r in rows]


# ---------------------------------------------------------------------------
# Notebooks
# ---------------------------------------------------------------------------
class NotebookOut(BaseModel):
    notebook_id: UUID
    workspace_id: UUID
    path: str
    created_at: datetime
    latest_version: UUID | None = None
    latest_saved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/notebooks")
async def list_notebooks(session: Session) -> list[NotebookOut]:
    notebooks = (
        await session.execute(select(Notebook).order_by(Notebook.created_at))
    ).scalars().all()
    # 노트북마다 최신 버전을 따로 조회한다(N+1). 목록 규모가 작다는 전제하의
    # 단순 구현 — 커지면 윈도우 함수로 묶는 최적화가 필요하다.
    out: list[NotebookOut] = []
    for nb in notebooks:
        latest = (
            await session.execute(
                select(NotebookVersion)
                .where(NotebookVersion.notebook_id == nb.notebook_id)
                .order_by(desc(NotebookVersion.saved_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        out.append(
            NotebookOut(
                notebook_id=nb.notebook_id,
                workspace_id=nb.workspace_id,
                path=nb.path,
                created_at=nb.created_at,
                latest_version=(latest.version_id if latest else None),
                latest_saved_at=(latest.saved_at if latest else None),
            )
        )
    return out


class NotebookCreate(BaseModel):
    workspace_id: UUID
    path: str = Field(min_length=1, max_length=512)
    content: dict[str, Any] = Field(default_factory=dict)


@router.post("/notebooks", status_code=201)
async def create_notebook(body: NotebookCreate, session: Session) -> NotebookOut:
    ws = await session.get(Workspace, body.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    nb_id = uuid4()
    session.add(
        Notebook(
            notebook_id=nb_id,
            workspace_id=body.workspace_id,
            path=body.path,
            created_by=ws.owner_user_id,
        )
    )
    await session.flush()

    # 생성 시 내용이 함께 왔으면 첫 버전을 저장하고 Git outbox에도 발신한다.
    # 빈 노트북이면 버전 없이 메타데이터만 만든다.
    if body.content:
        svc = NotebookService(session)
        await svc.save_and_emit_outbox(
            notebook_id=nb_id,
            content=body.content,
            saved_by=ws.owner_user_id,
            commit_message="initial",
        )
    await session.commit()
    return NotebookOut(
        notebook_id=nb_id,
        workspace_id=body.workspace_id,
        path=body.path,
        created_at=datetime.utcnow(),
        latest_version=None,
        latest_saved_at=None,
    )


class NotebookSaveRequest(BaseModel):
    content: dict[str, Any]
    saved_by: UUID
    commit_message: str | None = None
    auto: bool = False


@router.post("/notebooks/{notebook_id}/versions")
async def save_notebook_version(
    notebook_id: UUID, body: NotebookSaveRequest, session: Session
) -> dict[str, Any]:
    nb = await session.get(Notebook, notebook_id)
    if nb is None:
        raise HTTPException(status_code=404, detail="notebook not found")
    svc = NotebookService(session)
    result = await svc.save_and_emit_outbox(
        notebook_id=notebook_id,
        content=body.content,
        saved_by=body.saved_by,
        is_autosave=body.auto,
        commit_message=body.commit_message,
    )
    await session.commit()
    if not result.ok:
        raise HTTPException(status_code=400, detail=str(result.error))
    return {"version_id": str(result.value)}


@router.get("/notebooks/{notebook_id}/latest")
async def latest_version(notebook_id: UUID, session: Session) -> dict[str, Any]:
    nb = await session.get(Notebook, notebook_id)
    if nb is None:
        raise HTTPException(status_code=404, detail="notebook not found")
    latest = (
        await session.execute(
            select(NotebookVersion)
            .where(NotebookVersion.notebook_id == notebook_id)
            .order_by(desc(NotebookVersion.saved_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is None:
        return {
            "notebook_id": str(notebook_id),
            "path": nb.path,
            "content": {},
            "saved_at": None,
        }
    return {
        "notebook_id": str(notebook_id),
        "path": nb.path,
        "version_id": str(latest.version_id),
        "content": latest.content,
        "saved_at": latest.saved_at.isoformat() if latest.saved_at else None,
        "git_commit_sha": latest.git_commit_sha,
    }


# ---------------------------------------------------------------------------
# Share links — used by the Viewer screen
# ---------------------------------------------------------------------------
class ShareLinkOut(BaseModel):
    link_id: UUID
    notebook_id: UUID
    permission: str
    created_at: datetime
    revoked_at: datetime | None
    audience_roles: list[str]


@router.get("/share")
async def list_share_links(session: Session) -> list[ShareLinkOut]:
    links = (
        await session.execute(select(ShareLink).order_by(desc(ShareLink.created_at)))
    ).scalars().all()
    audience_rows = (await session.execute(select(ShareAudience))).scalars().all()
    by_link: dict[UUID, list[str]] = {}
    for a in audience_rows:
        if a.subject_role:
            by_link.setdefault(a.link_id, []).append(a.subject_role)
    return [
        ShareLinkOut(
            link_id=l.link_id,
            notebook_id=l.notebook_id,
            permission=l.permission,
            created_at=l.created_at,
            revoked_at=l.revoked_at,
            audience_roles=by_link.get(l.link_id, []),
        )
        for l in links
    ]


@router.get("/share/{link_id}")
async def resolve_share_link(link_id: UUID, session: Session) -> dict[str, Any]:
    # 폐기됐거나 없는 링크는 존재 여부를 숨기려 동일하게 404로 응답한다.
    link = await session.get(ShareLink, link_id)
    if link is None or link.revoked_at is not None:
        raise HTTPException(status_code=404, detail="link not found or revoked")
    nb = await session.get(Notebook, link.notebook_id)
    if nb is None:
        raise HTTPException(status_code=404, detail="notebook missing")
    latest = (
        await session.execute(
            select(NotebookVersion)
            .where(NotebookVersion.notebook_id == nb.notebook_id)
            .order_by(desc(NotebookVersion.saved_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    return {
        "link_id": str(link_id),
        "permission": link.permission,
        "notebook": {
            "notebook_id": str(nb.notebook_id),
            "path": nb.path,
        },
        "content": latest.content if latest else {},
        "saved_at": latest.saved_at.isoformat() if latest and latest.saved_at else None,
    }


class ShareLinkCreate(BaseModel):
    notebook_id: UUID
    permission: str
    audience_roles: list[str] = Field(default_factory=list)


@router.post("/share", status_code=201)
async def create_share_link(body: ShareLinkCreate, session: Session) -> ShareLinkOut:
    nb = await session.get(Notebook, body.notebook_id)
    if nb is None:
        raise HTTPException(status_code=404, detail="notebook not found")
    if body.permission not in ("read", "execute", "edit"):
        raise HTTPException(status_code=422, detail="invalid permission")
    if not body.audience_roles:
        raise HTTPException(status_code=422, detail="audience_roles required")
    link_id = uuid4()
    session.add(
        ShareLink(
            link_id=link_id,
            notebook_id=body.notebook_id,
            permission=body.permission,
            created_by=nb.created_by,
        )
    )
    for role in body.audience_roles:
        session.add(
            ShareAudience(
                audience_id=uuid4(),
                link_id=link_id,
                subject_user_id=None,
                subject_role=role,
            )
        )
    await session.commit()
    return ShareLinkOut(
        link_id=link_id,
        notebook_id=body.notebook_id,
        permission=body.permission,
        created_at=datetime.utcnow(),
        revoked_at=None,
        audience_roles=body.audience_roles,
    )
