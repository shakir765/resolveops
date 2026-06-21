from __future__ import annotations

import logging

from opentelemetry._logs import get_logger_provider, set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource

from resolveops_core.config import settings

_LOG_CONFIGURED = False


def setup_log_export(service_name: str) -> None:
    """Export stdlib logs to OTLP (collector -> Loki)."""
    global _LOG_CONFIGURED
    if _LOG_CONFIGURED or not settings.otel_enabled or not settings.otel_logs_enabled:
        return

    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            DEPLOYMENT_ENVIRONMENT: settings.environment,
            "service.namespace": "resolveops",
        }
    )
    provider = LoggerProvider(resource=resource)
    exporter = OTLPLogExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        insecure=settings.otel_exporter_otlp_insecure,
    )
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    set_logger_provider(provider)

    handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
    logging.getLogger().addHandler(handler)
    _LOG_CONFIGURED = True


def shutdown_log_export() -> None:
    global _LOG_CONFIGURED
    provider = get_logger_provider()
    if isinstance(provider, LoggerProvider):
        provider.shutdown()
    _LOG_CONFIGURED = False
