import asyncio

from opentelemetry.trace import SpanKind

from resolveops_core.config import settings
from resolveops_core.logging import get_logger
from resolveops_core.telemetry import get_tracer, instrument_httpx, setup_observability, shutdown_observability

setup_observability("resolveops-graph-worker", settings.log_level)
instrument_httpx()
logger = get_logger(__name__)


def _tracer():
    return get_tracer(__name__)


from resolveops_core.db.models import SessionLocal, init_db
from resolveops_core.graph.runner import GraphRunner
from resolveops_core.infra.queue import TicketQueue
from resolveops_core.infra.redis_client import redis_client
from resolveops_core.worker.guards import is_run_already_completed, wait_for_ticket_lock


async def handle_job(payload: dict) -> None:
    ticket_id = payload["ticket_id"]
    run_id = payload.get("run_id")
    lock_key = f"lock:ticket:{ticket_id}"

    with _tracer().start_as_current_span(
        "worker.process_ticket",
        kind=SpanKind.CONSUMER,
        attributes={
            "ticket.id": ticket_id,
            "run.id": run_id or "",
        },
    ):
        await wait_for_ticket_lock(redis_client, lock_key, ticket_id)

        try:
            session = SessionLocal()
            try:
                if is_run_already_completed(session, run_id):
                    logger.info(
                        "worker.duplicate_already_completed",
                        ticket_id=ticket_id,
                        run_id=run_id,
                    )
                    return
            finally:
                session.close()

            runner = GraphRunner(with_checkpoint=True)
            await asyncio.to_thread(runner.run, payload)
        finally:
            redis_client.release_lock(lock_key)


async def main() -> None:
    init_db()
    queue = TicketQueue()
    await queue.connect()
    logger.info("worker.started", queue=settings.ticket_queue_name)
    try:
        await queue.consume(handle_job)
    finally:
        shutdown_observability()


if __name__ == "__main__":
    asyncio.run(main())
