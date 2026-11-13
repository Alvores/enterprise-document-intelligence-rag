from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from phoenix.otel import register

from backend.app.core.config import settings
from backend.app.core.logging import logger


def setup_telemetry() -> None:
    """Configures OpenTelemetry tracing and binds LlamaIndex instrumentation."""
    # Check if tracing is enabled via environment (useful for skipping in CI/CD)
    if not settings.ENABLE_TELEMETRY:
        logger.info("Telemetry disabled via ENABLE_TELEMETRY flag.")
        return

    collector_endpoint = settings.PHOENIX_COLLECTOR_ENDPOINT

    try:
        logger.info(
            "Initializing OpenTelemetry TracerProvider...",
            extra={"endpoint": collector_endpoint, "project": settings.APP_NAME},
        )

        # 1. Register TracerProvider with Arize Phoenix OTLP endpoint
        tracer_provider = register(
            project_name=settings.APP_NAME,
            endpoint=collector_endpoint,
        )

        # 2. Hook LlamaIndex event dispatcher to the OpenTelemetry provider
        LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info("LlamaIndex OpenTelemetry instrumentation active.")
    except Exception as e:
        # Prevent telemetry network errors from crashing the API during startup
        logger.warning(
            "Failed to initialize OpenTelemetry tracing. Continuing without tracing.",
            extra={"error": str(e)},
        )
