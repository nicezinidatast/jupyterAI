"""감사 emitter 프로토콜 — 구체 구현은 audit-unit(OutboxAuditEmitter)에 있다."""

from __future__ import annotations

from typing import Any, Protocol

from dataplatform_shared.audit.events import DomainEvent


class AuditEventEmitter(Protocol):
    """구현체는 이벤트를 호출자의 DB 트랜잭션에 묶인 아웃박스(outbox)에 적재한다.

    아웃박스 패턴: 비즈니스 변경과 감사 이벤트를 같은 트랜잭션에 함께 커밋해,
    한쪽만 성공하는 불일치를 없애고 이후 별도 워커가 이벤트를 안전하게 발행한다.

    첫 인자 ``session``을 일부러 ``Any``로 둔 이유: audit-unit의 SQLAlchemy
    세션과 테스트용 가짜가 둘 다 이 계약을 만족하게 하면서, SQLAlchemy 의존이
    shared-lib로 새어 들어오지 않게(의존성 누출 차단) 하기 위함이다.
    """

    async def emit(self, session: Any, event: DomainEvent) -> None: ...
