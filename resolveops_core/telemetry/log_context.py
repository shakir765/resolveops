from __future__ import annotations

import structlog
from opentelemetry import trace


def bind_log_context(*, service_name: str, environment: str | None = None) -> None:
    """Bind stable fields included on every log line for this process."""
    fields: dict[str, str] = {"service": service_name}
    if environment:
        fields["environment"] = environment
    structlog.contextvars.bind_contextvars(**fields)


def add_otel_trace_context(_logger, _method_name: str, event_dict: dict) -> dict:
    """Inject trace/span IDs from the active OpenTelemetry span."""
    span = trace.get_current_span()
    context = span.get_span_context()
    if context.is_valid:
        event_dict["trace_id"] = format(context.trace_id, "032x")
        event_dict["span_id"] = format(context.span_id, "016x")
    return event_dict
