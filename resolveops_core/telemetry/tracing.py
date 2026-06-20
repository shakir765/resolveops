from __future__ import annotations

from typing import Any

from opentelemetry import context as context_api
from opentelemetry import trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagate import extract, inject, set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from resolveops_core.config import settings

_CONFIGURED = False


def setup_tracing(service_name: str) -> None:
    """Configure OTLP trace export and W3C trace context propagation."""
    global _CONFIGURED
    if _CONFIGURED or not settings.otel_enabled:
        return

    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            DEPLOYMENT_ENVIRONMENT: settings.environment,
            "service.namespace": "resolveops",
        }
    )
    sampler = ParentBasedTraceIdRatio(settings.otel_traces_sample_ratio)
    provider = TracerProvider(resource=resource, sampler=sampler)
    exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        insecure=settings.otel_exporter_otlp_insecure,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    set_global_textmap(
        CompositePropagator(
            [
                TraceContextTextMapPropagator(),
                W3CBaggagePropagator(),
            ]
        )
    )
    _CONFIGURED = True


def shutdown_tracing() -> None:
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.shutdown()


def instrument_fastapi(app: Any) -> None:
    if not settings.otel_enabled:
        return
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)


def instrument_httpx() -> None:
    if not settings.otel_enabled:
        return
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    HTTPXClientInstrumentor().instrument()


def get_tracer(name: str):
    return trace.get_tracer(name)


def inject_trace_context(carrier: dict[str, str] | None = None) -> dict[str, str]:
    merged = dict(carrier or {})
    inject(merged)
    return {key: str(value) for key, value in merged.items()}


def extract_trace_context(carrier: dict[str, Any] | None):
    normalized = {str(key): str(value) for key, value in (carrier or {}).items()}
    return extract(normalized)


def attach_trace_context(carrier: dict[str, Any] | None):
    return context_api.attach(extract_trace_context(carrier))


def detach_trace_context(token: context_api.Token) -> None:
    context_api.detach(token)
