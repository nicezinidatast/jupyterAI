"""Prometheus 메트릭 헬퍼 (NFR-SL-OBS-01).

플랫폼 전역에서 공통으로 쓰는 두 메트릭(요청 수·요청 지연)을 미리 선언해 둔다.
단위별 고유 메트릭은 각 단위에 둔다. 메트릭 이름은
``<unit>_<concept>_<unit_of_measure>`` 규칙을 따라 일관성을 유지한다.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

# 전용 레지스트리를 두는 이유: prometheus_client의 전역 기본 레지스트리에
# 섞이면 서드파티 라이브러리가 등록한 메트릭과 충돌하거나 중복 등록 에러가
# 날 수 있다. 플랫폼 메트릭만 격리해 /metrics 출력을 깨끗하게 유지한다.
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
    """Prometheus /metrics 핸들러용 ``(body, content_type)`` 튜플을 반환한다.

    프레임워크에 묶이지 않도록 raw 바이트와 콘텐츠 타입만 돌려준다 — 각 단위는
    이 값을 자기 웹 프레임워크의 응답으로 감싸기만 하면 된다.
    """
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
