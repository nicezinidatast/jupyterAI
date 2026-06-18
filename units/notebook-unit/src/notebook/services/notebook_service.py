"""NotebookService — 노트북 저장 + 같은 트랜잭션에서 Git 자동 커밋 outbox 발신.

해싱으로 ``save_and_emit_outbox``를 멱등하게 만든다. 새 내용의 SHA-256이
직전 버전과 같으면 새 버전 행을 만들지 않고 건너뛴다. 자동 저장(autosave)이
같은 내용을 반복해서 보내도 버전·outbox 행이 불어나지 않게 하기 위함이다.

버전 행과 outbox(발신함) 행을 같은 트랜잭션에 함께 넣는 것이 핵심이다.
이렇게 해야 "버전은 저장됐는데 Git push 요청은 누락" 같은 불일치가 생기지
않는다 — outbox 패턴의 원자성 보장.
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
    # 내용 지문(SHA-256). sort_keys로 키 순서를, separators로 공백을 정규화해
    # 의미가 같은 dict는 표현이 달라도 같은 해시가 나오게 한다 — 멱등 비교의 토대.
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class NotebookService:
    """노트북 버전 저장과 Git 커밋 outbox 발신을 묶는 서비스."""

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

        # 직전(최신) 버전과 지문을 비교해 변경 여부를 판단한다.
        latest = await self._session.scalar(
            select(NotebookVersion)
            .where(NotebookVersion.notebook_id == notebook_id)
            .order_by(desc(NotebookVersion.saved_at))
            .limit(1)
        )
        if latest is not None and latest.content_sha256 == digest:
            # 멱등 경로: 같은 내용을 또 저장한 것이므로 새 행을 만들지 않고
            # 기존 version_id를 그대로 돌려준다(버전·outbox 증식 방지).
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
        # outbox 행: 버전 insert와 반드시 같은 트랜잭션에서 추가한다.
        # 둘이 함께 커밋되거나 함께 롤백돼야 push 누락/유령 push가 안 생긴다.
        self._session.add(
            GitCommitOutbox(
                notebook_version_id=version_id,
                commit_message=commit_message,
                state="queued",
            )
        )
        await self._session.flush()
        return Ok(version_id)
