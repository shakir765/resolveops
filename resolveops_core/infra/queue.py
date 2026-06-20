import json
from typing import Any

import aio_pika
from opentelemetry.trace import SpanKind, Status, StatusCode

from resolveops_core.config import settings
from resolveops_core.logging import get_logger
from resolveops_core.telemetry import (
    attach_trace_context,
    detach_trace_context,
    get_tracer,
    inject_trace_context,
)
from resolveops_core.worker.exceptions import LockWaitTimeout

logger = get_logger(__name__)


def _tracer():
    return get_tracer(__name__)


def _header_dict(headers: Any) -> dict[str, str]:
    if not headers:
        return {}
    return {str(key): str(value) for key, value in headers.items()}


class TicketQueue:
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

    async def publish(self, payload: dict[str, Any]) -> None:
        if not self._channel:
            await self.connect()
        assert self._channel is not None

        with _tracer().start_as_current_span(
            "queue.publish",
            kind=SpanKind.PRODUCER,
            attributes={
                "messaging.system": "rabbitmq",
                "messaging.destination": self.queue_name,
                "ticket.id": payload.get("ticket_id", ""),
            },
        ):
            message = aio_pika.Message(
                body=json.dumps(payload).encode("utf-8"),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
                headers=inject_trace_context(),
            )
            await self._channel.default_exchange.publish(message, routing_key=self.queue_name)
        logger.info("queue.published", queue=self.queue_name, ticket_id=payload.get("ticket_id"))

    async def consume(self, handler) -> None:
        if not self._channel:
            await self.connect()
        assert self._channel is not None
        queue = await self._channel.declare_queue(self.queue_name, durable=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                payload = json.loads(message.body.decode("utf-8"))
                ticket_id = payload.get("ticket_id")
                token = attach_trace_context(_header_dict(message.headers))
                try:
                    with _tracer().start_as_current_span(
                        "queue.process",
                        kind=SpanKind.CONSUMER,
                        attributes={
                            "messaging.system": "rabbitmq",
                            "messaging.destination": self.queue_name,
                            "ticket.id": ticket_id or "",
                        },
                    ) as span:
                        try:
                            await handler(payload)
                        except LockWaitTimeout as exc:
                            span.set_status(Status(StatusCode.ERROR, "lock wait timeout"))
                            logger.warning(
                                "queue.requeue_lock_timeout",
                                ticket_id=exc.ticket_id,
                                lock_key=exc.lock_key,
                            )
                            await message.nack(requeue=True)
                        except Exception:
                            span.set_status(Status(StatusCode.ERROR, "handler failed"))
                            span.record_exception()
                            logger.exception("queue.handler_failed", ticket_id=ticket_id)
                            await message.nack(requeue=False)
                        else:
                            await message.ack()
                finally:
                    detach_trace_context(token)
