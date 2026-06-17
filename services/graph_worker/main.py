import asyncio

from resolveops_core.config import settings
from resolveops_core.db.models import SessionLocal, init_db
from resolveops_core.graph.runner import GraphRunner
from resolveops_core.infra.queue import TicketQueue
from resolveops_core.infra.redis_client import redis_client
from resolveops_core.logging import configure_logging, get_logger
from resolveops_core.worker.guards import is_run_already_completed, wait_for_ticket_lock

configure_logging(settings.log_level)
logger = get_logger(__name__)


async def handle_job(payload: dict) -> None:
    ticket_id = payload["ticket_id"]
    run_id = payload.get("run_id")
    lock_key = f"lock:ticket:{ticket_id}"

    await wait_for_ticket_lock(redis_client, lock_key, ticket_id)

    try:
        x=3000
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
    await queue.consume(handle_job)


if __name__ == "__main__":
    asyncio.run(main())
