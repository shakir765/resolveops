from resolveops_core.telemetry.log_context import add_otel_trace_context, bind_log_context
from resolveops_core.telemetry.tracing import (
    attach_trace_context,
    detach_trace_context,
    get_tracer,
    inject_trace_context,
    instrument_fastapi,
    instrument_httpx,
    setup_tracing,
    shutdown_tracing,
)

__all__ = [
    "add_otel_trace_context",
    "attach_trace_context",
    "bind_log_context",
    "detach_trace_context",
    "get_tracer",
    "inject_trace_context",
    "instrument_fastapi",
    "instrument_httpx",
    "setup_observability",
    "setup_tracing",
    "shutdown_observability",
    "shutdown_tracing",
]


def __getattr__(name: str):
    if name in ("setup_observability", "shutdown_observability"):
        from resolveops_core.telemetry import setup as setup_module

        return getattr(setup_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
