"""Audit emitter interface + event types (concrete impl lives in audit-unit)."""

from dataplatform_shared.audit.emitter_iface import AuditEventEmitter
from dataplatform_shared.audit.events import DomainEvent, EventResult, make_event

__all__ = ["AuditEventEmitter", "DomainEvent", "EventResult", "make_event"]
