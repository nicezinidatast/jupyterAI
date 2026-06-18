"""BackupService의 상태 전이 테스트: running → success/failed.

pg_dump 실행 환경과 무관하게 Backup 행의 상태 전이가 올바른지 검증한다.
인메모리 SQLite를 사용하므로 실제 PostgreSQL 없이도 실행 가능하다.
"""

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
    """인메모리 SQLite 세션 픽스처.

    테스트마다 독립적인 인메모리 DB를 생성한다.
    expire_on_commit=False: 커밋 후에도 ORM 객체 속성에 접근 가능하도록 한다.
    테스트 종료 시 엔진을 dispose해 연결 풀을 정리한다.
    """
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
    """pg_dump 바이너리가 없거나 대상 호스트에 연결할 수 없으면 Err를 반환하고
    Backup 행의 state가 'failed'이며 error 필드가 채워진다.

    검증 포인트:
    - 반환값이 Err인지 (성공 가장 없음).
    - DB에 Backup 행이 존재하는지 (1단계 커밋이 실패해도 행은 남아야 함).
    - state == 'failed'인지.
    - error 필드가 비어있지 않은지 (운영자가 원인을 알 수 있어야 함).
    """
    svc = BackupService(
        session=session,
        backup_dir=tmp_path,
        db_url="postgresql://test@localhost/test",
        db_password=Secret("ignored"),
    )
    result = await svc.run_meta_db_backup()
    # pg_dump가 없거나 호스트에 연결할 수 없는 환경에서는 반드시 Err여야 한다.
    assert isinstance(result, Err)

    from sqlalchemy import select

    backup = await session.scalar(select(Backup).limit(1))
    assert backup is not None
    assert backup.state == "failed"
    # error 필드에 원인 문자열이 있어야 운영자가 실패 이유를 알 수 있다.
    assert backup.error
