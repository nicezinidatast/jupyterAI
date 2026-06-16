"""Telemetry helpers: structured logging, Prometheus metrics, OpenTelemetry tracing."""

from dataplatform_shared.telemetry.logging import (
    bind_corr_id,
    configure_logging,
    get_corr_id,
    get_logger,
)
from dataplatform_shared.telemetry.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    metrics_endpoint,
)
from dataplatform_shared.telemetry.tracing import configure_tracing, get_tracer

__all__ = [
    "configure_logging",
    "bind_corr_id",
    "get_corr_id",
    "get_logger",
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "metrics_endpoint",
    "configure_tracing",
    "get_tracer",
]
