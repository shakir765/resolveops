from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from resolveops_core.db.models import SessionLocal
from resolveops_core.db.repository import TicketRepository
from resolveops_core.integrations.ticketing import JiraClient, ServiceNowClient
from resolveops_core.config import settings
from resolveops_core.infra.queue import TicketQueue

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
queue = TicketQueue()


class WebhookPayload(BaseModel):
    ticket_id: str
    title: str | None = None
    description: str | None = None
    user_id: str | None = None


@router.post("/servicenow/{ticket_number}")
async def servicenow_webhook(ticket_number: str):
    client = ServiceNowClient()
    data = client.get_ticket(ticket_number)
    session = SessionLocal()
    try:
        ticket_repo = TicketRepository(session)
        existing = ticket_repo.get_ticket(data["ticket_id"])
        if not existing:
            ticket = ticket_repo.create_ticket(data)
        else:
            ticket = existing
        from resolveops_core.db.repository import WorkflowRepository

        workflow_repo = WorkflowRepository(session)
        run = workflow_repo.create_run(ticket.id, ticket.tenant_id, settings.prompt_version)
        job = {**data, "tenant_id": ticket.tenant_id, "run_id": run.id, "thread_id": run.thread_id}
        await queue.connect()
        await queue.publish(job)
        return {"queued": True, "ticket_id": ticket.id, "run_id": run.id}
    finally:
        session.close()


@router.post("/jira/{issue_key}")
async def jira_webhook(issue_key: str):
    client = JiraClient()
    data = client.get_ticket(issue_key)
    session = SessionLocal()
    try:
        ticket_repo = TicketRepository(session)
        existing = ticket_repo.get_ticket(data["ticket_id"])
        ticket = existing or ticket_repo.create_ticket(data)
        from resolveops_core.db.repository import WorkflowRepository

        workflow_repo = WorkflowRepository(session)
        run = workflow_repo.create_run(ticket.id, ticket.tenant_id, settings.prompt_version)
        job = {**data, "tenant_id": ticket.tenant_id, "run_id": run.id, "thread_id": run.thread_id}
        await queue.connect()
        await queue.publish(job)
        return {"queued": True, "ticket_id": ticket.id, "run_id": run.id}
    finally:
        session.close()
