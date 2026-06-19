from __future__ import annotations

from resolveops_core.config import settings
from resolveops_core.messaging.kafka_adapter import KafkaTicketQueue
from resolveops_core.messaging.protocol import TicketJobQueue
from resolveops_core.messaging.rabbitmq_adapter import RabbitMQTicketQueue


def get_ticket_queue() -> TicketJobQueue:
    backend = settings.queue_backend.lower()
    if backend == "rabbitmq":
        return RabbitMQTicketQueue()
    if backend == "kafka":
        return KafkaTicketQueue()
    raise ValueError(f"Unsupported QUEUE_BACKEND: {settings.queue_backend}")
