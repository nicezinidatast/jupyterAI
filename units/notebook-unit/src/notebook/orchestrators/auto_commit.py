"""Background loop that drains GitCommitOutbox via GitAdapter."""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.telemetry import get_logger

from notebook.adapters.git import GitAdapter
from notebook.models import GitCommitOutbox, Notebook, NotebookVersion, Workspace

logger = get_logger("notebook.auto_commit")

MAX_ATTEMPTS = 3


class AutoCommitOrchestrator:
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
        self._token_provider = token_provider  # async callable returning Secret
        self._batch = batch
        self._stopped = asyncio.Event()

    def stop(self) -> None:
        self._stopped.set()

    async def run(self, idle_seconds: float = 5.0) -> None:
        while not self._stopped.is_set():
            processed = await self._drain_once()
            if processed == 0:
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=idle_seconds)
                except TimeoutError:
                    pass

    async def _drain_once(self) -> int:
        async with self._session_factory() as session:  # type: AsyncSession
            async with session.begin():
                stmt = (
                    select(GitCommitOutbox)
                    .where(GitCommitOutbox.state == "queued")
                    .order_by(GitCommitOutbox.created_at)
                    .limit(self._batch)
                )
                # Match audit-unit's consumer: ``FOR UPDATE SKIP LOCKED`` so
                # two workers can drain in parallel without claiming the same
                # row. sqlite ignores the clause silently in tests.
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

        token = await self._token_provider(version.saved_by)
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
            version.git_commit_sha = result.value
            row.state = "committed"
            row.updated_at = func.now()  # type: ignore[assignment]
            logger.info("git_commit_pushed", version_id=str(version.version_id))
            return

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
