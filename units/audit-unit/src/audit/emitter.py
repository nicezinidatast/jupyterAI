"""Outbox 패턴 기반 기본 이미터(emitter) — 이벤트를 audit_outbox 테이블에 삽입한다.

Outbox 패턴이란: 도메인 변경과 이벤트 발행을 하나의 DB 트랜잭션으로 묶어
메시지 손실 없이 at-least-once 전달을 보장하는 패턴이다.
이미터는 outbox 행을 삽입하기만 하며, 실제 audit_log로 이동시키는 작업은
백그라운드 컨슈머(OutboxConsumer)가 담당한다.
"""

from __future__ import annotations

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.audit.events import DomainEvent

from audit.models import AuditOutbox


class OutboxAuditEmitter:
    """shared-lib의 ``AuditEventEmitter`` Protocol을 구현하는 기본 이미터.

    핵심 보장: 이미터가 자체 트랜잭션을 열지 않는다. 호출자의 세션이 커밋을
    결정하므로 도메인 변경과 audit 행이 하나의 원자적 트랜잭션으로 묶인다.
    즉, 도메인 변경이 롤백되면 outbox 행도 함께 사라져 허위 이벤트가 남지 않는다.
    """

    async def emit(self, session: AsyncSession, event: DomainEvent) -> None:
        """호출자 세션에 outbox 행을 삽입한다.

        event는 JSONB로 직렬화되어 저장된다. 커밋은 호출자 책임이다.
        """
        await session.execute(insert(AuditOutbox).values(event=event))
