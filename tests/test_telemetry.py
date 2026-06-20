from opentelemetry import trace
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from resolveops_core.telemetry.tracing import (
    _CONFIGURED,
    attach_trace_context,
    detach_trace_context,
    inject_trace_context,
    setup_tracing,
)


def _reset_tracing(monkeypatch, *, enabled: bool) -> None:
    import resolveops_core.telemetry.tracing as tracing_module

    monkeypatch.setattr(tracing_module.settings, "otel_enabled", enabled)
    tracing_module._CONFIGURED = False
    trace.set_tracer_provider(TracerProvider())
    set_global_textmap(CompositePropagator([TraceContextTextMapPropagator()]))


def test_inject_extract_roundtrip(monkeypatch):
    _reset_tracing(monkeypatch, enabled=False)
    tracer = trace.get_tracer("test")

    with tracer.start_as_current_span("parent") as span:
        carrier = inject_trace_context()
        assert "traceparent" in carrier

        token = attach_trace_context(carrier)
        try:
            with tracer.start_as_current_span("child") as child:
                assert child.get_span_context().trace_id == span.get_span_context().trace_id
        finally:
            detach_trace_context(token)


def test_setup_tracing_disabled(monkeypatch):
    _reset_tracing(monkeypatch, enabled=False)
    setup_tracing("resolveops-test")

    provider = trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider)
    assert _CONFIGURED is False
