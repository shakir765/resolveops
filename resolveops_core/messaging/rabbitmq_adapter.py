from __future__ import annotations

import json
from typing import Any

import aio_pika

from resolveops_core.config import settings
from resolveops_core.logging import get_logger
from resolveops_core.messaging.protocol import JobHandler
from resolveops_core.messaging.types import AckAction, QueueMessage, TicketJob

logger = get_logger(__name__)


class RabbitMQTicketQueue:
    """RabbitMQ implementation of TicketJobQueue."""

    def __init__(self, url: str | None = None, queue_name: str | None = None):
        self.url = url or settings.rabbitmq_url
        self.queue_name = queue_name or settings.ticket_queue_name
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self.url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)
        await self._channel.declare_queue(self.queue_name, durable=True)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None

    async def publish(
        self,
        job: TicketJob,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        if not self._channel:
            await self.connect()
        assert self._channel is not None

        amqp_headers: dict[str, Any] | None = None
        if headers:
            amqp_headers = dict(headers)

        message = aio_pika.Message(
            body=json.dumps(job.to_dict()).encode("utf-8"),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
            headers=amqp_headers,
        )
        await self._channel.default_exchange.publish(message, routing_key=self.queue_name)
        logger.info("queue.published", queue=self.queue_name, ticket_id=job.ticket_id)

    async def consume(self, handler: JobHandler) -> None:
        if not self._channel:
            await self.connect()
        assert self._channel is not None

        queue = await self._channel.declare_queue(self.queue_name, durable=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                payload = json.loads(message.body.decode("utf-8"))
                queue_message = QueueMessage(
                    job=TicketJob.from_dict(payload),
                    delivery_tag=str(message.delivery_tag),
                    headers=_stringify_headers(message.headers),
                    raw={"delivery_tag": message.delivery_tag},
                )
                ticket_id = queue_message.job.ticket_id
                try:
                    action = await handler(queue_message)
                except Exception:
                    logger.exception("queue.handler_failed", ticket_id=ticket_id)
                    await message.nack(requeue=False)
                    continue

                if action == AckAction.RETRY:
                    logger.warning(
                        "queue.requeue",
                        ticket_id=ticket_id,
                        queue=self.queue_name,
                    )
                    await message.nack(requeue=True)
                elif action == AckAction.REJECT:
                    logger.warning(
                        "queue.reject",
                        ticket_id=ticket_id,
                        queue=self.queue_name,
                    )
                    await message.nack(requeue=False)
                else:
                    await message.ack()


def _stringify_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    if not headers:
        return {}
    return {str(key): str(value) for key, value in headers.items()}
