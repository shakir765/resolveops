from __future__ import annotations

from resolveops_core.messaging.protocol import JobHandler
from resolveops_core.messaging.types import TicketJob


class KafkaTicketQueue:
    """Placeholder for a future Kafka adapter. Switch via QUEUE_BACKEND=kafka."""

    async def connect(self) -> None:
        raise NotImplementedError(
            "Kafka queue backend is not implemented. Set QUEUE_BACKEND=rabbitmq."
        )

    async def close(self) -> None:
        return None

    async def publish(
        self,
        job: TicketJob,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        raise NotImplementedError(
            "Kafka queue backend is not implemented. Set QUEUE_BACKEND=rabbitmq."
        )

    async def consume(self, handler: JobHandler) -> None:
        raise NotImplementedError(
            "Kafka queue backend is not implemented. Set QUEUE_BACKEND=rabbitmq."
        )
