"""OpenTelemetry 트레이싱 래퍼 (NFR-SL-OBS-03).

``otlp_endpoint``가 비어 있으면 익스포터 없이 프로바이더만 설치하므로 사실상
no-op(아무 곳에도 안 보냄)이라 import·구성 비용이 싸다. 운영 배포에서만 env로
엔드포인트를 지정해 실제 수집기로 스팬을 보낸다. 덕분에 로컬·테스트 환경은
트레이싱 인프라 없이도 그대로 돌아간다.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_configured = False


def configure_tracing(service_name: str, otlp_endpoint: str | None = None) -> None:
    """멱등(idempotent) — 다시 호출하면 리소스 속성만 갱신한다."""
    global _configured
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        # OTLP 익스포터 패키지가 깔려 있지 않은 프로젝트도 이 모듈 자체는
        # import할 수 있도록, 익스포터는 엔드포인트가 있을 때만 지연 import한다.
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(provider)
    _configured = True


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
