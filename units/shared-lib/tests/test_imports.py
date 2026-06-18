"""스모크 테스트 — 모든 공개 하위 모듈이 import되는지 확인한다.

가장 흔한 회귀(re-export 누락·순환 import·선택적 의존성 깨짐)를 빠르게 잡는
얕고 넓은 안전망. 로직이 아니라 "import 표면이 멀쩡한가"만 본다.
"""

from __future__ import annotations


def test_top_level_imports() -> None:
    from dataplatform_shared import (
        DomainError,
        Err,
        Ok,
        Result,
        and_then,
        map_ok,
        safe_boundary,
    )

    assert Ok and Err and Result and and_then and map_ok and DomainError and safe_boundary


def test_telemetry_imports() -> None:
    from dataplatform_shared.telemetry import (
        REQUEST_COUNT,
        REQUEST_LATENCY,
        configure_logging,
        configure_tracing,
        get_logger,
        get_tracer,
        metrics_endpoint,
    )

    assert configure_logging and configure_tracing and metrics_endpoint
    assert get_logger and get_tracer
    assert REQUEST_COUNT and REQUEST_LATENCY


def test_security_imports() -> None:
    from dataplatform_shared.security import (
        RateLimiter,
        SecurityKernel,
        SlidingWindowLimiter,
    )
    from dataplatform_shared.security.secret import Secret

    assert SecurityKernel and Secret and RateLimiter and SlidingWindowLimiter


def test_audit_imports() -> None:
    from dataplatform_shared.audit import AuditEventEmitter, DomainEvent, make_event

    assert AuditEventEmitter and DomainEvent and make_event


def test_types_imports() -> None:
    from dataplatform_shared.types import CorrelationId, Role, SessionId, UserContext, UserId

    assert UserId and Role and CorrelationId and SessionId and UserContext


def test_idempotency_imports() -> None:
    from dataplatform_shared.idempotency import idempotency_key

    assert idempotency_key("u", "op", {}) is not None
