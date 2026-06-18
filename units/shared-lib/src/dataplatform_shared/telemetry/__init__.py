"""텔레메트리 헬퍼: 구조화 로깅, Prometheus 메트릭, OpenTelemetry 트레이싱.

관측성(observability)의 세 기둥(로그·메트릭·트레이스)을 단위 전반에서 동일한
방식으로 쓰도록 한곳에 모은 패키지. 각 단위는 여기 export된 헬퍼만 쓰고
구체 백엔드(structlog/prometheus_client/opentelemetry)에 직접 의존하지 않는다.
"""

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
