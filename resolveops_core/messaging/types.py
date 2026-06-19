from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AckAction(str, Enum):
    """Broker-agnostic delivery outcome from a job handler."""

    ACK = "ack"
    RETRY = "retry"
    REJECT = "reject"


@dataclass
class TicketJob:
    ticket_id: str
    tenant_id: str = "default"
    title: str = ""
    description: str = ""
    user_id: str = ""
    source: str = "api"
    run_id: str = ""
    thread_id: str = ""
    prompt_version: str = "v1"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TicketJob:
        return cls(
            ticket_id=data["ticket_id"],
            tenant_id=data.get("tenant_id", "default"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            user_id=data.get("user_id", ""),
            source=data.get("source", "api"),
            run_id=data.get("run_id", ""),
            thread_id=data.get("thread_id", ""),
            prompt_version=data.get("prompt_version", "v1"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "description": self.description,
            "user_id": self.user_id,
            "source": self.source,
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "prompt_version": self.prompt_version,
        }


@dataclass
class QueueMessage:
    job: TicketJob
    delivery_tag: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
