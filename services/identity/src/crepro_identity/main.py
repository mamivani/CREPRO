from crepro_common import create_app
from crepro_common.config import get_settings
from crepro_common.telemetry import init_tracing
from crepro_identity.api import router

settings = get_settings()

# Initialize OpenTelemetry tracing if enabled
init_tracing(
    service_name="crepro-identity",
    jaeger_host=settings.jaeger_host,
    jaeger_port=settings.jaeger_port,
    enabled=settings.opentelemetry_enabled,
)

app = create_app("identity")
app.include_router(router)

