"""Backup orchestration. ``pg_dump`` is invoked via subprocess but the secret
is passed via env, never argv (NFR-AM-SEC-03)."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret
from dataplatform_shared.telemetry import get_logger

from admin_backend.models import Backup

logger = get_logger("admin.backup")


class BackupService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        backup_dir: Path,
        db_url: str,
        db_password: Secret,
    ) -> None:
        self._session = session
        self._backup_dir = backup_dir
        self._db_url = db_url
        self._db_password = db_password

    async def run_meta_db_backup(self) -> Result[UUID, DomainError]:
        """Run pg_dump and record the outcome.

        Each phase uses its own transaction so a long-running ``pg_dump`` does
        not hold a DB row lock for minutes. The caller is **not** expected to
        own the session's transaction lifecycle — this service deliberately
        commits its own marker rows so the backup history is durable even if
        the orchestrator process is killed mid-dump.
        """
        backup_id = uuid4()

        # 1) Record the run as "running" and commit so the row is visible.
        async with self._session.begin():
            self._session.add(Backup(backup_id=backup_id, target="meta_db", state="running"))

        output_path = self._backup_dir / f"{backup_id}.dump"
        env = {**os.environ, "PGPASSWORD": self._db_password.reveal()}
        argv = [
            "pg_dump",
            "--format=custom",
            f"--file={output_path}",
            self._db_url,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            ok = proc.returncode == 0
            error = None if ok else stderr.decode(errors="replace")
        except FileNotFoundError:
            ok = False
            error = "pg_dump not installed in this environment"
        except Exception as e:  # noqa: BLE001
            ok = False
            error = str(e)

        size = output_path.stat().st_size if output_path.exists() else 0
        new_state = "success" if ok else "failed"

        # 2) Update the run with the terminal state in its own short transaction.
        async with self._session.begin():
            await self._session.execute(
                update(Backup)
                .where(Backup.backup_id == backup_id)
                .values(
                    ended_at=func.now(),
                    state=new_state,
                    size_bytes=size,
                    location=str(output_path) if ok else None,
                    error=error,
                )
            )

        if not ok:
            logger.error("backup_failed", target="meta_db", error=error)
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        return Ok(backup_id)
