import pytest

from resolveops_core.messaging.factory import get_ticket_queue
from resolveops_core.messaging.kafka_adapter import KafkaTicketQueue
from resolveops_core.messaging.rabbitmq_adapter import RabbitMQTicketQueue


def test_factory_returns_rabbitmq_by_default():
    queue = get_ticket_queue()
    assert isinstance(queue, RabbitMQTicketQueue)


def test_factory_returns_kafka_when_configured(monkeypatch):
    monkeypatch.setenv("QUEUE_BACKEND", "kafka")
    from resolveops_core.config import Settings

    settings = Settings()
    assert settings.queue_backend == "kafka"

    from resolveops_core.messaging import factory

    monkeypatch.setattr(factory.settings, "queue_backend", "kafka")
    queue = factory.get_ticket_queue()
    assert isinstance(queue, KafkaTicketQueue)


def test_factory_rejects_unknown_backend(monkeypatch):
    from resolveops_core.messaging import factory

    monkeypatch.setattr(factory.settings, "queue_backend", "sqs")
    with pytest.raises(ValueError, match="Unsupported QUEUE_BACKEND"):
        factory.get_ticket_queue()
