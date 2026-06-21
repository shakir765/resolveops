from __future__ import annotations

import logging
import sys

import structlog

from resolveops_core.config import settings
from resolveops_core.telemetry.log_context import add_otel_trace_context, bind_log_context
from resolveops_core.telemetry.log_export import setup_log_export


def configure_logging(level: str = "INFO", service_name: str | None = None) -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)

    if service_name:
        bind_log_context(service_name=service_name, environment=settings.environment)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        add_otel_trace_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
    ]

    use_otlp_logs = settings.otel_enabled and settings.otel_logs_enabled and service_name

    if use_otlp_logs:
        logging.basicConfig(format="%(message)s", level=log_level, stream=sys.stdout, force=True)
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            cache_logger_on_first_use=True,
        )

        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)

        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(log_level)
        root.addHandler(stdout_handler)

        setup_log_export(service_name)
    else:
        logging.basicConfig(format="%(message)s", level=log_level, force=True)
        structlog.configure(
            processors=[*shared_processors, structlog.processors.JSONRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str):
    return structlog.get_logger(name)
