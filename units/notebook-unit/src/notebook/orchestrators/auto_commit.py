"""GitAdapter를 통해 GitCommitOutbox를 비워 내는 백그라운드 루프.

노트북 저장(트랜잭션)과 Git 커밋(외부 HTTP 호출)을 한 트랜잭션으로 묶지
않으려고 outbox 패턴을 쓴다. 저장 트랜잭션은 outbox(발신함)에 행 하나만
남기고 곧장 커밋되며, 실제 Git push는 이 오케스트레이터가 비동기로 처리한다.
이렇게 분리해야 외부 Git 서버가 느리거나 죽어도 노트북 저장 자체는 막히지 않고,
push 실패는 재시도로 흡수된다.

멱등성(idempotent): outbox 행은 ``queued`` 상태에서만 집어 가고, 성공하면
``committed``로 바꾼다. 같은 행을 두 번 push해도 GitAdapter 쪽에서 동일 내용은
새 커밋을 만들지 않으므로(blob sha 비교) 중복 커밋이 생기지 않는다.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.telemetry import get_logger

from notebook.adapters.git import GitAdapter
from notebook.models import GitCommitOutbox, Notebook, NotebookVersion, Workspace

logger = get_logger("notebook.auto_commit")

# push가 연속 실패하면 더 시도하지 않고 ``failed``로 못 박는 임계치.
# 무한 재시도로 죽은 outbox 행이 워커를 영원히 점유하는 것을 막는다.
MAX_ATTEMPTS = 3


class AutoCommitOrchestrator:
    """outbox를 폴링해 Git push를 수행하는 백그라운드 워커.

    계약: 한 번에 ``batch`` 개씩 ``queued`` 행을 잠그고(FOR UPDATE SKIP LOCKED)
    처리한다. 처리할 행이 없으면 ``idle_seconds`` 만큼 쉬므로 빈 폴링 부하를
    줄인다. ``stop()``으로 깰 수 있어 종료가 즉시 반영된다.
    """

    def __init__(
        self,
        session_factory,
        git: GitAdapter,
        token_provider,
        *,
        batch: int = 50,
    ) -> None:
        self._session_factory = session_factory
        self._git = git
        # 커밋 작성자(version.saved_by)별 Git 토큰을 비동기로 돌려주는 콜러블.
        # 토큰을 미리 들고 있지 않고 push 직전에 조회해 짧게만 노출한다.
        self._token_provider = token_provider  # async callable returning Secret
        self._batch = batch
        self._stopped = asyncio.Event()

    def stop(self) -> None:
        # 종료 신호. run 루프와 대기 중인 sleep을 동시에 깨운다.
        self._stopped.set()

    async def run(self, idle_seconds: float = 5.0) -> None:
        # 메인 루프: 큐를 비우고, 빈 큐면 잠깐 쉰다.
        while not self._stopped.is_set():
            processed = await self._drain_once()
            if processed == 0:
                # 한 건도 처리 못 했으면 idle_seconds 대기. 단, sleep 대신
                # stop 이벤트를 기다려 종료 신호가 오면 즉시 빠져나온다.
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=idle_seconds)
                except TimeoutError:
                    pass

    async def _drain_once(self) -> int:
        # 한 배치를 한 트랜잭션으로 처리하고 처리 건수를 돌려준다.
        async with self._session_factory() as session:  # type: AsyncSession
            async with session.begin():
                # 오래된 것부터(created_at 순) 처리해 발신 순서를 대략 유지한다.
                stmt = (
                    select(GitCommitOutbox)
                    .where(GitCommitOutbox.state == "queued")
                    .order_by(GitCommitOutbox.created_at)
                    .limit(self._batch)
                )
                # audit-unit 소비자와 동일하게 ``FOR UPDATE SKIP LOCKED``를 써서
                # 두 워커가 같은 행을 집지 않고 병렬로 큐를 비울 수 있게 한다.
                # sqlite는 이 절을 조용히 무시하므로 테스트(단일 워커)엔 무해하다.
                try:
                    stmt = stmt.with_for_update(skip_locked=True)
                except Exception:  # pragma: no cover
                    pass
                rows = (await session.execute(stmt)).scalars().all()
                if not rows:
                    return 0
                for row in rows:
                    await self._process_one(session, row)
                return len(rows)

    async def _process_one(self, session: AsyncSession, row: GitCommitOutbox) -> None:
        # outbox 행 한 건을 push로 변환한다. 참조 무결성이 깨진 경우
        # (버전·노트북·워크스페이스가 사라짐)는 재시도해도 소용없으므로
        # 곧장 ``failed``로 못 박는다 — 재시도 대상은 일시적 외부 오류뿐.
        version = await session.get(NotebookVersion, row.notebook_version_id)
        if version is None:
            row.state = "failed"
            row.last_error = "version_missing"
            return
        notebook = await session.get(Notebook, version.notebook_id)
        if notebook is None:
            row.state = "failed"
            row.last_error = "notebook_missing"
            return
        workspace = await session.get(Workspace, notebook.workspace_id)
        if workspace is None:
            row.state = "failed"
            row.last_error = "workspace_missing"
            return

        # 토큰은 push 직전에만 조회해 메모리 노출 시간을 최소화한다.
        token = await self._token_provider(version.saved_by)
        # 커밋 메시지가 없으면 경로 + 저장 시각으로 자동 생성한다.
        message = row.commit_message or f"auto: {notebook.path} @ {version.saved_at.isoformat()}"
        result = await self._git.commit_and_push(
            repo_url=workspace.git_repo_url,
            branch=workspace.git_branch,
            path=notebook.path,
            content=version.content,
            message=message,
            author=str(version.saved_by),
            token=token,
        )
        if result.ok:
            # 성공: 새 커밋 SHA를 버전에 기록하고 행을 ``committed``로 종료.
            # 다음 폴링에서 이 행은 다시 집히지 않는다(멱등성 보장).
            version.git_commit_sha = result.value
            row.state = "committed"
            row.updated_at = func.now()  # type: ignore[assignment]
            logger.info("git_commit_pushed", version_id=str(version.version_id))
            return

        # 실패: 시도 횟수를 올리고 마지막 오류를 남긴다. ``queued``로 두면
        # 다음 배치에서 자동 재시도되고, 임계치를 넘으면 ``failed``로 멈춘다.
        row.attempts += 1
        row.last_error = str(result.error)
        row.updated_at = func.now()  # type: ignore[assignment]
        if row.attempts >= MAX_ATTEMPTS:
            row.state = "failed"
            logger.error(
                "git_commit_failed_terminally",
                version_id=str(version.version_id),
                attempts=row.attempts,
            )
