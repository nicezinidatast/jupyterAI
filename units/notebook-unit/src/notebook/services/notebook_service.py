"""NotebookService — save notebook + same-tx outbox emit for Git auto-commit.

The hashing makes ``save_and_emit_outbox`` idempotent: if the new content has
the same SHA-256 as the latest version, we skip the insert.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result

from notebook.models import GitCommitOutbox, NotebookVersion


def content_sha256(content: dict[str, Any]) -> str:
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class NotebookService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_and_emit_outbox(
        self,
        *,
        notebook_id: UUID,
        content: dict[str, Any],
        saved_by: UUID,
        is_autosave: bool = False,
        commit_message: str | None = None,
    ) -> Result[UUID, DomainError]:
        digest = content_sha256(content)

        latest = await self._session.scalar(
            select(NotebookVersion)
            .where(NotebookVersion.notebook_id == notebook_id)
            .order_by(desc(NotebookVersion.saved_at))
            .limit(1)
        )
        if latest is not None and latest.content_sha256 == digest:
            # No-op: identical content was already saved.
            return Ok(latest.version_id)

        version_id = uuid4()
        self._session.add(
            NotebookVersion(
                version_id=version_id,
                notebook_id=notebook_id,
                content_sha256=digest,
                content=content,
                saved_by=saved_by,
                is_autosave=is_autosave,
            )
        )
        # Outbox row: SAME transaction as the version insert.
        self._session.add(
            GitCommitOutbox(
                notebook_version_id=version_id,
                commit_message=commit_message,
                state="queued",
            )
        )
        await self._session.flush()
        return Ok(version_id)
