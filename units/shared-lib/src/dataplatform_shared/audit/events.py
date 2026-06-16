"""Standard ``DomainEvent`` envelope.

Producers fill in payload as a JSON-serialisable mapping that MUST NOT contain
``Secret`` values — a runtime guard in :func:`make_event` enforces this.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from dataplatform_shared.security.secret import Secret
from dataplatform_shared.types.common import CorrelationId, UserId

EventResult = Literal["success", "failure"]


class DomainEvent(TypedDict):
    """Standard envelope for an auditable event.

    ``at`` is an ISO-8601 UTC string so the schema is portable across DB layers
    and queue payloads.
    """

    type: str
    actor: str
    resource: str | None
    result: EventResult
    at: str
    corr_id: str
    payload: dict[str, Any]


def _scrub_payload(payload: dict[str, Any], path: str = "") -> None:
    """Refuse Secret values anywhere in the payload tree."""
    for key, value in payload.items():
        if isinstance(value, Secret):
            raise ValueError(f"DomainEvent payload contains Secret at {path}/{key}")
        if isinstance(value, dict):
            _scrub_payload(value, f"{path}/{key}")


def make_event(
    *,
    type: str,
    actor: UserId | str,
    result: EventResult,
    corr_id: CorrelationId | str,
    resource: str | None = None,
    payload: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> DomainEvent:
    safe_payload = dict(payload or {})
    _scrub_payload(safe_payload)
    return DomainEvent(
        type=type,
        actor=str(actor),
        resource=resource,
        result=result,
        at=(at or datetime.now(UTC)).isoformat(),
        corr_id=str(corr_id),
        payload=safe_payload,
    )
