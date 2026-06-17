from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Protocol

from resolveops_core.config import settings
from resolveops_core.db.repository import WorkflowRepository
from resolveops_core.logging import get_logger
from resolveops_core.worker.exceptions import LockWaitTimeout

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)


class LockClient(Protocol):
    def acquire_lock(self, key: str, ttl: int | None = None) -> bool: ...


def is_run_already_completed(session: Session, run_id: str | None) -> bool:
    if not run_id:
        return False
    return WorkflowRepository(session).is_completed(run_id)


async def wait_for_ticket_lock(
    redis_client: LockClient,
    lock_key: str,
    ticket_id: str,
) -> None:
    deadline = time.monotonic() + settings.lock_wait_timeout_seconds
    poll_interval = settings.lock_poll_interval_seconds

    while not redis_client.acquire_lock(lock_key):
        if time.monotonic() >= deadline:
            logger.warning(
                "worker.lock_wait_timeout",
                ticket_id=ticket_id,
                lock_key=lock_key,
                timeout_seconds=settings.lock_wait_timeout_seconds,
            )
            raise LockWaitTimeout(ticket_id=ticket_id, lock_key=lock_key)

        logger.info("worker.waiting_for_lock", ticket_id=ticket_id, lock_key=lock_key)
        await asyncio.sleep(poll_interval)

    logger.info("worker.lock_acquired", ticket_id=ticket_id, lock_key=lock_key)
