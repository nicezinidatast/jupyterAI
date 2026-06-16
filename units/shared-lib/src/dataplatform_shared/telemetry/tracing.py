"""OpenTelemetry tracing wrapper (NFR-SL-OBS-03).

When ``otlp_endpoint`` is empty the SDK still installs a no-op provider so the
import is cheap; production deployments set the endpoint via env.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_configured = False


def configure_tracing(service_name: str, otlp_endpoint: str | None = None) -> None:
    """Idempotent — subsequent calls update only resource attributes."""
    global _configured
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        # Import here so projects without the OTLP exporter can still import the module.
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(provider)
    _configured = True


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
