import json

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from resolveops_core.telemetry.log_context import add_otel_trace_context, bind_log_context


def test_add_otel_trace_context_adds_ids_when_span_active():
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer("test")

    with tracer.start_as_current_span("test-span") as span:
        event = add_otel_trace_context(None, "info", {"event": "worker.started"})
        assert event["trace_id"] == format(span.get_span_context().trace_id, "032x")
        assert event["span_id"] == format(span.get_span_context().span_id, "016x")


def test_add_otel_trace_context_omits_ids_without_span():
    trace.set_tracer_provider(TracerProvider())
    event = add_otel_trace_context(None, "info", {"event": "idle"})
    assert "trace_id" not in event
    assert "span_id" not in event


def test_bind_log_context_merges_service_fields():
    structlog.contextvars.clear_contextvars()
    bind_log_context(service_name="resolveops-api", environment="test")
    event = structlog.contextvars.merge_contextvars(None, "info", {"event": "boot"})
    assert event["service"] == "resolveops-api"
    assert event["environment"] == "test"


def test_configure_logging_emits_trace_id_in_json_output(monkeypatch, capsys):
    import resolveops_core.logging as logging_module
    import resolveops_core.telemetry.tracing as tracing_module

    monkeypatch.setattr(tracing_module.settings, "otel_enabled", False)
    monkeypatch.setattr(tracing_module.settings, "otel_logs_enabled", False)
    tracing_module._CONFIGURED = False

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer("test")

    logging_module.configure_logging("INFO", service_name="resolveops-test")
    logger = logging_module.get_logger("test")

    with tracer.start_as_current_span("request"):
        logger.info("queue.published", ticket_id="INC-1")

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["event"] == "queue.published"
    assert payload["service"] == "resolveops-test"
    assert "trace_id" in payload
    assert len(payload["trace_id"]) == 32
