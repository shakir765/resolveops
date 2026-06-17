from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from resolveops_core.worker.exceptions import LockWaitTimeout
from resolveops_core.worker.guards import is_run_already_completed, wait_for_ticket_lock


@pytest.mark.asyncio
async def test_wait_for_ticket_lock_acquires_immediately():
    redis_client = MagicMock()
    redis_client.acquire_lock.return_value = True

    await wait_for_ticket_lock(redis_client, "lock:ticket:t1", "t1")

    redis_client.acquire_lock.assert_called_once_with("lock:ticket:t1")


@pytest.mark.asyncio
async def test_wait_for_ticket_lock_retries_until_acquired():
    redis_client = MagicMock()
    redis_client.acquire_lock.side_effect = [False, False, True]

    with patch("resolveops_core.worker.guards.settings") as mock_settings:
        mock_settings.lock_poll_interval_seconds = 0
        mock_settings.lock_wait_timeout_seconds = 10
        await wait_for_ticket_lock(redis_client, "lock:ticket:t1", "t1")

    assert redis_client.acquire_lock.call_count == 3


@pytest.mark.asyncio
async def test_wait_for_ticket_lock_raises_on_timeout():
    redis_client = MagicMock()
    redis_client.acquire_lock.return_value = False

    with patch("resolveops_core.worker.guards.settings") as mock_settings:
        mock_settings.lock_poll_interval_seconds = 0
        mock_settings.lock_wait_timeout_seconds = 0
        with pytest.raises(LockWaitTimeout) as exc_info:
            await wait_for_ticket_lock(redis_client, "lock:ticket:t1", "t1")

    assert exc_info.value.ticket_id == "t1"
    assert exc_info.value.lock_key == "lock:ticket:t1"


def test_is_run_already_completed_when_run_finished():
    session = MagicMock()
    completed_run = MagicMock(completed_at=datetime.now(timezone.utc))

    with patch("resolveops_core.worker.guards.WorkflowRepository") as repo_cls:
        repo_cls.return_value.is_completed.return_value = True
        assert is_run_already_completed(session, "run-1") is True
        repo_cls.return_value.is_completed.assert_called_once_with("run-1")


def test_is_run_already_completed_when_run_in_progress():
    session = MagicMock()

    with patch("resolveops_core.worker.guards.WorkflowRepository") as repo_cls:
        repo_cls.return_value.is_completed.return_value = False
        assert is_run_already_completed(session, "run-1") is False


def test_is_run_already_completed_without_run_id():
    session = MagicMock()
    assert is_run_already_completed(session, None) is False


@pytest.mark.asyncio
async def test_handle_job_skips_when_run_already_completed():
    from services.graph_worker.main import handle_job

    payload = {"ticket_id": "t1", "run_id": "run-1", "thread_id": "t1:run-1"}

    with (
        patch("services.graph_worker.main.wait_for_ticket_lock", new_callable=AsyncMock),
        patch("services.graph_worker.main.SessionLocal") as session_local,
        patch("services.graph_worker.main.is_run_already_completed", return_value=True),
        patch("services.graph_worker.main.redis_client") as redis_client,
        patch("services.graph_worker.main.GraphRunner") as graph_runner,
    ):
        session_local.return_value = MagicMock()
        await handle_job(payload)

    graph_runner.assert_not_called()
    redis_client.release_lock.assert_called_once_with("lock:ticket:t1")


@pytest.mark.asyncio
async def test_handle_job_runs_graph_when_not_completed():
    from services.graph_worker.main import handle_job

    payload = {"ticket_id": "t1", "run_id": "run-1", "thread_id": "t1:run-1"}
    runner_instance = MagicMock()
    runner_instance.run.return_value = {"status": "resolved"}

    with (
        patch("services.graph_worker.main.wait_for_ticket_lock", new_callable=AsyncMock),
        patch("services.graph_worker.main.SessionLocal") as session_local,
        patch("services.graph_worker.main.is_run_already_completed", return_value=False),
        patch("services.graph_worker.main.redis_client") as redis_client,
        patch("services.graph_worker.main.GraphRunner", return_value=runner_instance) as graph_runner,
        patch("services.graph_worker.main.asyncio.to_thread", new_callable=AsyncMock) as to_thread,
    ):
        session_local.return_value = MagicMock()
        await handle_job(payload)

    graph_runner.assert_called_once_with(with_checkpoint=True)
    to_thread.assert_awaited_once_with(runner_instance.run, payload)
    redis_client.release_lock.assert_called_once_with("lock:ticket:t1")


@pytest.mark.asyncio
async def test_queue_requeues_on_lock_wait_timeout():
    from resolveops_core.infra.queue import TicketQueue

    message = AsyncMock()
    message.body = b'{"ticket_id": "t1", "run_id": "run-1"}'

    async def handler(_payload):
        raise LockWaitTimeout(ticket_id="t1", lock_key="lock:ticket:t1")

    queue = TicketQueue()
    queue._channel = MagicMock()

    async def one_message_iterator():
        yield message

    queue_iter = MagicMock()
    queue_iter.__aenter__ = AsyncMock(return_value=one_message_iterator())
    queue_iter.__aexit__ = AsyncMock(return_value=False)

    declared_queue = MagicMock()
    declared_queue.iterator.return_value = queue_iter
    queue._channel.declare_queue = AsyncMock(return_value=declared_queue)

    await queue.consume(handler)

    message.nack.assert_awaited_once_with(requeue=True)
    message.ack.assert_not_awaited()


@pytest.mark.asyncio
async def test_queue_acks_on_successful_handler():
    from resolveops_core.infra.queue import TicketQueue

    message = AsyncMock()
    message.body = b'{"ticket_id": "t1", "run_id": "run-1"}'

    async def handler(_payload):
        return None

    queue = TicketQueue()
    queue._channel = MagicMock()

    async def one_message_iterator():
        yield message

    queue_iter = MagicMock()
    queue_iter.__aenter__ = AsyncMock(return_value=one_message_iterator())
    queue_iter.__aexit__ = AsyncMock(return_value=False)

    declared_queue = MagicMock()
    declared_queue.iterator.return_value = queue_iter
    queue._channel.declare_queue = AsyncMock(return_value=declared_queue)

    await queue.consume(handler)

    message.ack.assert_awaited_once()
    message.nack.assert_not_awaited()
