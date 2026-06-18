"""감사(audit) emitter 인터페이스 + 이벤트 타입.

구체 구현(OutboxAuditEmitter 등)은 audit-unit에 있다. shared-lib에는 모든
단위가 같은 이벤트 형식과 emit 계약을 따르도록 하는 인터페이스와 이벤트
타입만 둔다.
"""

from dataplatform_shared.audit.emitter_iface import AuditEventEmitter
from dataplatform_shared.audit.events import DomainEvent, EventResult, make_event

__all__ = ["AuditEventEmitter", "DomainEvent", "EventResult", "make_event"]
