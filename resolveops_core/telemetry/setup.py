from __future__ import annotations

from resolveops_core.config import settings
from resolveops_core.telemetry.log_export import shutdown_log_export
from resolveops_core.telemetry.tracing import setup_tracing, shutdown_tracing


def setup_observability(service_name: str, log_level: str | None = None) -> None:
    """Configure tracing (Phase 1) and correlated log export (Phase 2)."""
    from resolveops_core.logging import configure_logging

    setup_tracing(service_name)
    configure_logging(log_level or settings.log_level, service_name=service_name)


def shutdown_observability() -> None:
    shutdown_log_export()
    shutdown_tracing()


__all__ = [
    "setup_observability",
    "shutdown_observability",
]
