"""OpenTelemetry instrumentation and tracing setup."""

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


def init_tracing(
    service_name: str,
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831,
    enabled: bool = True,
):
    """Initialize OpenTelemetry tracing with Jaeger exporter."""
    if not enabled or not OTEL_AVAILABLE:
        return

    try:
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )

        trace_provider = TracerProvider()
        trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        trace.set_tracer_provider(trace_provider)

        FastAPIInstrumentor.instrument()
        HTTPXClientInstrumentor.instrument()
    except Exception:
        pass  # Silently skip if OpenTelemetry is not properly configured


def get_tracer(name: str):
    """Get a tracer for the given module name."""
    if not OTEL_AVAILABLE:
        return None
    return trace.get_tracer(name)

