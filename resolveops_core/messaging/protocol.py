from __future__ import annotations

from typing import Awaitable, Callable, Protocol

from resolveops_core.messaging.types import AckAction, QueueMessage, TicketJob

JobHandler = Callable[[QueueMessage], Awaitable[AckAction]]


class TicketJobQueue(Protocol):
    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def publish(
        self,
        job: TicketJob,
        *,
        headers: dict[str, str] | None = None,
    ) -> None: ...

    async def consume(self, handler: JobHandler) -> None: ...
