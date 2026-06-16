"""Backup row transitions through running → success/failed."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dataplatform_shared.result import Err
from dataplatform_shared.security.secret import Secret

from admin_backend.models import Backup, Base
from admin_backend.services.backup_service import BackupService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_backup_without_pg_dump_marks_failed(session: AsyncSession, tmp_path: Path) -> None:
    svc = BackupService(
        session=session,
        backup_dir=tmp_path,
        db_url="postgresql://test@localhost/test",
        db_password=Secret("ignored"),
    )
    result = await svc.run_meta_db_backup()
    # pg_dump pointed at an unreachable host (or absent binary) must produce
    # Err and a "failed" row with a populated error string.
    assert isinstance(result, Err)

    from sqlalchemy import select

    backup = await session.scalar(select(Backup).limit(1))
    assert backup is not None
    assert backup.state == "failed"
    assert backup.error
