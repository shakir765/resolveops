class LockWaitTimeout(Exception):
    """Raised when a worker cannot acquire a ticket lock within the configured deadline."""

    def __init__(self, ticket_id: str, lock_key: str) -> None:
        self.ticket_id = ticket_id
        self.lock_key = lock_key
        super().__init__(f"Timed out waiting for lock {lock_key} (ticket_id={ticket_id})")
