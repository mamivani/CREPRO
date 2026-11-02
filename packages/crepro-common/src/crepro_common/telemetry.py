"""OpenTelemetry basics shared by every service (15-day plan, Day 5).

Tracing is opt-in: with no `CREPRO_OTEL_EXPORTER_ENDPOINT` configured, the global tracer
provider is left at OpenTelemetry's no-op default, so every service runs with zero tracing
overhead and no dependency on a collector being up. Setting that env var (e.g. to an OTLP
collector in Dev/Azure) turns on real span export without any code change.
"""

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from crepro_common.config import get_settings


def configure_tracing(service_name: str) -> None:
    settings = get_settings()
    if not settings.otel_exporter_endpoint:
        return
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return  # Already configured; avoid resetting the provider across repeated create_app calls.
    provider = TracerProvider(resource=Resource.create({"service.name": f"crepro-{service_name}"}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint))
    )
    trace.set_tracer_provider(provider)


def instrument_app(app: FastAPI, service_name: str) -> None:
    configure_tracing(service_name)
    FastAPIInstrumentor.instrument_app(app)
