"""Saving identical content twice yields a single notebook_version row."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from notebook.models import Base, GitCommitOutbox, Notebook, NotebookVersion, Workspace
from notebook.services.notebook_service import NotebookService, content_sha256

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        # Seed a workspace + notebook.
        ws_id = uuid4()
        nb_id = uuid4()
        s.add(
            Workspace(
                workspace_id=ws_id,
                owner_user_id=uuid4(),
                kind="personal",
                name="ws1",
                git_repo_url="https://git.test/repo",
                git_branch="main",
            )
        )
        s.add(
            Notebook(
                notebook_id=nb_id,
                workspace_id=ws_id,
                path="analysis.ipynb",
                created_by=uuid4(),
            )
        )
        await s.commit()
        s.notebook_id = nb_id  # type: ignore[attr-defined] — convenience for tests
        yield s
    await engine.dispose()


async def test_identical_save_is_idempotent(session: AsyncSession) -> None:
    svc = NotebookService(session)
    user = uuid4()
    content = {"cells": [{"type": "code", "source": "1+1"}]}
    r1 = await svc.save_and_emit_outbox(
        notebook_id=session.notebook_id,  # type: ignore[attr-defined]
        content=content,
        saved_by=user,
    )
    await session.commit()
    r2 = await svc.save_and_emit_outbox(
        notebook_id=session.notebook_id,  # type: ignore[attr-defined]
        content=content,
        saved_by=user,
    )
    await session.commit()
    assert r1.ok and r2.ok
    assert r1.value == r2.value  # same version id returned

    versions = await session.scalar(select(func.count()).select_from(NotebookVersion))
    outbox = await session.scalar(select(func.count()).select_from(GitCommitOutbox))
    assert versions == 1
    assert outbox == 1


async def test_changed_content_creates_new_version(session: AsyncSession) -> None:
    svc = NotebookService(session)
    user = uuid4()
    await svc.save_and_emit_outbox(
        notebook_id=session.notebook_id,  # type: ignore[attr-defined]
        content={"a": 1},
        saved_by=user,
    )
    await svc.save_and_emit_outbox(
        notebook_id=session.notebook_id,  # type: ignore[attr-defined]
        content={"a": 2},
        saved_by=user,
    )
    await session.commit()
    versions = await session.scalar(select(func.count()).select_from(NotebookVersion))
    outbox = await session.scalar(select(func.count()).select_from(GitCommitOutbox))
    assert versions == 2
    assert outbox == 2


def test_content_sha256_is_dict_order_independent() -> None:
    a = {"a": 1, "b": 2}
    b = {"b": 2, "a": 1}
    assert content_sha256(a) == content_sha256(b)
