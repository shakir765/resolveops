"""Sync LangGraph runtime state with PostgreSQL system-of-record."""

from __future__ import annotations

from typing import Any

from resolveops_core.db.repository import TicketRepository, WorkflowRepository
from resolveops_core.graph.state import (
    TicketState,
    run_status_from_state,
    snapshot_for_audit,
)


class StateStore:
    """Persists distilled state to PostgreSQL alongside LangGraph Redis checkpoints."""

    def __init__(self, ticket_repo: TicketRepository, workflow_repo: WorkflowRepository):
        self.ticket_repo = ticket_repo
        self.workflow_repo = workflow_repo

    def sync_after_step(
        self,
        run_id: str,
        agent_name: str,
        state_before: TicketState,
        patch: dict[str, Any],
        state_after: TicketState,
    ) -> None:
        self.workflow_repo.log_event(run_id, state_after["ticket_id"], agent_name, "state_before", snapshot_for_audit(state_before))
        self.workflow_repo.log_event(run_id, state_after["ticket_id"], agent_name, "state_patch", patch)
        self.workflow_repo.log_event(run_id, state_after["ticket_id"], agent_name, "state_after", snapshot_for_audit(state_after))
        self.workflow_repo.update_run_progress(
            run_id,
            current_step=state_after.get("current_step"),
            state_version=state_after.get("state_version"),
            status=run_status_from_state(state_after),
        )
        self.ticket_repo.update_from_state(state_after["ticket_id"], state_after)

    def sync_run_completion(self, run_id: str, final_state: TicketState) -> None:
        self.ticket_repo.update_from_state(final_state["ticket_id"], final_state)
        self.workflow_repo.update_run_progress(
            run_id,
            current_step=final_state.get("current_step"),
            state_version=final_state.get("state_version"),
            status="completed" if run_status_from_state(final_state) == "completed" else "paused",
        )
        if run_status_from_state(final_state) == "completed":
            self.workflow_repo.mark_completed(run_id, final_state.get("status", "completed"))

    def sync_run_failure(self, run_id: str, ticket_id: str, error: str) -> None:
        self.workflow_repo.mark_completed(run_id, "failed", error=error)
        self.ticket_repo.update_from_state(ticket_id, {"status": "failed", "error": error})

    def sync_interrupt(self, run_id: str, state: TicketState, next_steps: tuple[Any, ...]) -> None:
        next_step = next_steps[0] if next_steps else state.get("current_step")
        self.ticket_repo.update_from_state(state["ticket_id"], state)
        self.workflow_repo.update_run_progress(
            run_id,
            current_step=str(next_step) if next_step else state.get("current_step"),
            state_version=state.get("state_version"),
            status="paused",
        )
        self.workflow_repo.log_event(
            run_id,
            state["ticket_id"],
            "system",
            "interrupt",
            {"next_steps": [str(s) for s in next_steps], "snapshot": snapshot_for_audit(state)},
        )
