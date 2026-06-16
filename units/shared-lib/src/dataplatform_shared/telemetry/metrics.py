"""Prometheus metrics helpers (NFR-SL-OBS-01).

Two cross-unit metrics are pre-declared; per-unit metrics live in each unit.
Metric names follow ``<unit>_<concept>_<unit_of_measure>``.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

# A dedicated registry isolates platform metrics from any 3rd-party defaults.
REGISTRY = CollectorRegistry(auto_describe=True)

REQUEST_COUNT: Counter = Counter(
    "platform_requests_total",
    "Total HTTP requests across the platform.",
    labelnames=("unit", "route", "method", "code"),
    registry=REGISTRY,
)

REQUEST_LATENCY: Histogram = Histogram(
    "platform_request_latency_seconds",
    "HTTP request latency in seconds.",
    labelnames=("unit", "route"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
    registry=REGISTRY,
)


def metrics_endpoint() -> tuple[bytes, str]:
    """Return ``(body, content_type)`` for a Prometheus /metrics handler."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
