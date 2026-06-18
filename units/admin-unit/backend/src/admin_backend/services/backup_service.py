"""백업 오케스트레이션 서비스.

``pg_dump``를 subprocess로 호출하지만, DB 비밀번호(Secret)는 환경 변수로만
전달하며 argv에는 절대 포함하지 않는다(보안 요구사항 NFR-AM-SEC-03).
프로세스 목록이나 감사 로그에 비밀번호가 노출되는 것을 방지하기 위해서다.

트랜잭션 분리 전략:
1단계 커밋(running 행 삽입)과 2단계 커밋(최종 상태 업데이트)을 별도 트랜잭션으로
분리한다. pg_dump가 오래 걸리는 동안 DB 락을 붙잡지 않으려는 의도다.
오케스트레이터 프로세스가 중간에 죽어도 1단계 행은 살아남아 운영자가 인지할 수 있다.
"""

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
    """PostgreSQL 메타 DB 백업을 오케스트레이션하는 서비스.

    pg_dump 호출 결과를 Backup 테이블에 기록하며, 호출자는 세션 트랜잭션
    생명주기를 직접 관리할 필요가 없다. 이 서비스가 내부에서 트랜잭션을
    스스로 커밋하기 때문이다.

    Args:
        session: SQLAlchemy 비동기 세션. 이 서비스가 트랜잭션 경계를 직접 관리한다.
        backup_dir: 덤프 파일을 저장할 디렉터리 경로.
        db_url: pg_dump에 전달할 PostgreSQL 연결 URL. 비밀번호는 포함하지 않는다.
        db_password: 비밀번호를 담은 Secret 객체. 환경 변수로만 전달된다.
    """

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
        """pg_dump를 실행하고 결과를 Backup 테이블에 기록한다.

        각 단계는 독립적인 트랜잭션을 사용한다.
        - 1단계: "running" 상태 행을 먼저 커밋 → pg_dump 진행 중에도 행이 가시적.
        - 2단계: pg_dump 완료 후 최종 상태(success/failed)로 업데이트.

        이렇게 두 트랜잭션으로 나누면 pg_dump가 수분 걸리는 동안 락을 붙잡지 않고,
        프로세스가 중간에 종료돼도 "running" 고아 행이 남아 운영자가 이상을 알 수 있다.

        호출자는 세션의 트랜잭션 생명주기를 소유하지 않는다.
        이 메서드가 트랜잭션을 직접 begin/commit하기 때문이다.

        Returns:
            Ok(backup_id): 백업 성공 시 생성된 UUID.
            Err(DomainError.EXTERNAL_UNAVAILABLE): pg_dump 실패 또는 미설치 시.
        """
        backup_id = uuid4()

        # 1단계: "running" 행을 커밋해 이력을 즉시 가시화한다.
        async with self._session.begin():
            self._session.add(Backup(backup_id=backup_id, target="meta_db", state="running"))

        output_path = self._backup_dir / f"{backup_id}.dump"
        # NFR-AM-SEC-03: 비밀번호는 환경 변수로만 전달 — argv에 포함하면 ps 출력에 노출된다.
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
            # pg_dump 바이너리가 이 환경에 설치되지 않은 경우.
            ok = False
            error = "pg_dump not installed in this environment"
        except Exception as e:  # noqa: BLE001
            # 기타 예외(권한 부족, OS 오류 등)는 문자열로 기록한다.
            ok = False
            error = str(e)

        # 파일이 생성됐으면 실제 크기를, 실패해서 파일이 없으면 0을 기록한다.
        size = output_path.stat().st_size if output_path.exists() else 0
        new_state = "success" if ok else "failed"

        # 2단계: 최종 상태를 단독 짧은 트랜잭션으로 업데이트한다.
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
