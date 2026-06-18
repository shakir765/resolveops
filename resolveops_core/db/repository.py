from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from resolveops_core.db.models import (
    IdempotencyKey,
    Ticket,
    TicketStatus,
    WorkflowEvent,
    WorkflowRun,
    new_id,
    sla_deadline_for_priority,
)
from resolveops_core.graph.state import build_thread_id


class TicketRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_ticket(self, payload: dict[str, Any]) -> Ticket:
        ticket = Ticket(
            id=payload["ticket_id"],
            tenant_id=payload.get("tenant_id", "default"),
            title=payload["title"],
            description=payload["description"],
            user_id=payload["user_id"],
            source=payload.get("source", "api"),
            status=TicketStatus.NEW.value,
            external_ref=payload.get("external_ref"),
            metadata_json=payload.get("metadata", {}),
        )
        self.session.add(ticket)
        self.session.commit()
        self.session.refresh(ticket)
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        return self.session.get(Ticket, ticket_id)

    def list_tickets(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[Ticket]:
        query = self.session.query(Ticket).order_by(Ticket.created_at.desc())
        if tenant_id:
            query = query.filter(Ticket.tenant_id == tenant_id)
        if user_id:
            query = query.filter(Ticket.user_id == user_id)
        return query.limit(limit).all()

    def update_from_state(self, ticket_id: str, state: dict[str, Any]) -> Optional[Ticket]:
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return None
        ticket.status = state.get("status", ticket.status)
        ticket.priority = state.get("priority", ticket.priority)
        ticket.category = state.get("category", ticket.category)
        ticket.ticket_type = state.get("ticket_type", ticket.ticket_type)
        ticket.diagnosis = state.get("diagnosis", ticket.diagnosis)
        ticket.resolution = state.get("resolution_plan", ticket.resolution)
        ticket.user_response = state.get("user_response", ticket.user_response)
        ticket.confidence = state.get("confidence", ticket.confidence)
        ticket.escalated = state.get("escalated", ticket.escalated)
        ticket.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(ticket)
        return ticket


class WorkflowRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_run(self, ticket_id: str, tenant_id: str, prompt_version: str) -> WorkflowRun:
        run_id = new_id("run-")
        thread_id = build_thread_id(ticket_id, run_id)
        run = WorkflowRun(
            id=run_id,
            ticket_id=ticket_id,
            tenant_id=tenant_id,
            thread_id=thread_id,
            status="queued",
            prompt_version=prompt_version,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        return self.session.get(WorkflowRun, run_id)

    def is_completed(self, run_id: str) -> bool:
        run = self.get_run(run_id)
        return bool(run and run.completed_at is not None)

    def get_run_by_thread(self, thread_id: str) -> Optional[WorkflowRun]:
        return self.session.query(WorkflowRun).filter(WorkflowRun.thread_id == thread_id).first()

    def list_runs_for_ticket(self, ticket_id: str) -> list[WorkflowRun]:
        return (
            self.session.query(WorkflowRun)
            .filter(WorkflowRun.ticket_id == ticket_id)
            .order_by(WorkflowRun.started_at.desc().nullslast())
            .all()
        )

    def mark_started(self, run_id: str) -> None:
        run = self.get_run(run_id)
        if run:
            run.status = "processing"
            run.started_at = datetime.now(timezone.utc)
            self.session.commit()

    def mark_completed(self, run_id: str, status: str, error: Optional[str] = None) -> None:
        run = self.get_run(run_id)
        if run:
            run.status = status
            run.completed_at = datetime.now(timezone.utc)
            run.error = error
            self.session.commit()

    def update_run_progress(
        self,
        run_id: str,
        *,
        current_step: Optional[str] = None,
        state_version: Optional[int] = None,
        status: Optional[str] = None,
    ) -> None:
        run = self.get_run(run_id)
        if not run:
            return
        if current_step is not None:
            run.current_step = current_step
        if state_version is not None:
            run.state_version = state_version
        if status is not None:
            run.status = status
        self.session.commit()

    def get_active_run(self, ticket_id: str) -> Optional[WorkflowRun]:
        return (
            self.session.query(WorkflowRun)
            .filter(
                WorkflowRun.ticket_id == ticket_id,
                WorkflowRun.status.in_(["queued", "processing", "paused"]),
            )
            .order_by(WorkflowRun.started_at.desc().nullslast())
            .first()
        )

    def log_event(
        self,
        run_id: str,
        ticket_id: str,
        agent_name: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> WorkflowEvent:
        event = WorkflowEvent(
            id=new_id("evt-"),
            run_id=run_id,
            ticket_id=ticket_id,
            agent_name=agent_name,
            event_type=event_type,
            payload=payload,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list_events(self, run_id: str) -> list[WorkflowEvent]:
        return (
            self.session.query(WorkflowEvent)
            .filter(WorkflowEvent.run_id == run_id)
            .order_by(WorkflowEvent.created_at.asc())
            .all()
        )


class IdempotencyRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_existing(self, tenant_id: str, key: str) -> Optional[IdempotencyKey]:
        return (
            self.session.query(IdempotencyKey)
            .filter(IdempotencyKey.tenant_id == tenant_id, IdempotencyKey.key == key)
            .first()
        )

    def store(self, tenant_id: str, key: str, resource_type: str, resource_id: str) -> IdempotencyKey:
        record = IdempotencyKey(
            id=new_id("idem-"),
            tenant_id=tenant_id,
            key=key,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record


def compute_sla_met(priority: Optional[str], completed_at: datetime, created_at: datetime) -> bool:
    if not priority:
        return True
    deadline = sla_deadline_for_priority(priority)
    # Compare against ticket creation + SLA window
    allowed = created_at + (deadline - datetime.now(timezone.utc))
    return completed_at <= allowed
