"""
ResolveOps API — entry point for IT ticket resolution.

This service is the HTTP gateway for the platform. It:
  1. Accepts tickets (API, ServiceNow/Jira import, webhooks via webhooks_router)
  2. Persists tickets and workflow runs in PostgreSQL
  3. Triggers LangGraph processing (async via RabbitMQ or sync inline)
  4. Exposes run state, HITL resume, and an admin dashboard

Heavy agent orchestration lives in services/graph_worker + resolveops_core/graph/.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from resolveops_core.config import settings
from resolveops_core.db.models import SessionLocal, init_db
from resolveops_core.db.repository import IdempotencyRepository, TicketRepository, WorkflowRepository
from resolveops_core.evaluation.metrics import EvaluationFramework
from resolveops_core.messaging import TicketJob, get_ticket_queue
from resolveops_core.integrations.ticketing import JiraClient, ServiceNowClient
from resolveops_core.logging import configure_logging, get_logger
from services.api.routes.webhooks import router as webhooks_router

configure_logging(settings.log_level)
logger = get_logger(__name__)
templates = Jinja2Templates(directory="services/api/templates")

# Shared job queue publisher — graph_worker consumes via the same backend.
queue = get_ticket_queue()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class TicketCreate(BaseModel):
    ticket_id: str | None = None
    tenant_id: str = Field(default_factory=lambda: settings.default_tenant_id)
    title: str
    description: str
    user_id: str
    source: str = "api"
    external_ref: str | None = None
    metadata: dict = Field(default_factory=dict)


class ProcessRequest(BaseModel):
    # True (default): publish job to the message queue for graph_worker.
    # False: run LangGraph inline in this request (useful for local debugging).
    async_mode: bool = True


class HumanFeedbackRequest(BaseModel):
    feedback: str


# ---------------------------------------------------------------------------
# App lifecycle — wire up DB tables and job queue on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await queue.connect()
    yield
    await queue.close()


app = FastAPI(title="ResolveOps API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ServiceNow / Jira webhook endpoints (auto-import + queue processing).
app.include_router(webhooks_router)


def _idempotency_key(request: Request, tenant_id: str) -> str | None:
    """Read standard idempotency header so duplicate POST /tickets are safe."""
    return request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api"}


# ---------------------------------------------------------------------------
# Ticket CRUD — create and query support tickets
# ---------------------------------------------------------------------------


@app.post("/tickets")
async def create_ticket(payload: TicketCreate, request: Request):
    session = SessionLocal()
    try:
        ticket_repo = TicketRepository(session)
        idem_repo = IdempotencyRepository(session)
        data = payload.model_dump()

        # Auto-generate ticket ID when caller does not supply one.
        if not data.get("ticket_id"):
            from resolveops_core.db.models import new_id

            data["ticket_id"] = new_id("INC-")

        # Return existing ticket when client retries with the same idempotency key.
        idem = _idempotency_key(request, data["tenant_id"])
        if idem:
            existing = idem_repo.get_existing(data["tenant_id"], idem)
            if existing:
                ticket = ticket_repo.get_ticket(existing.resource_id)
                return {"ticket": _serialize_ticket(ticket), "idempotent": True}

        ticket = ticket_repo.create_ticket(data)
        if idem:
            idem_repo.store(data["tenant_id"], idem, "ticket", ticket.id)
        return {"ticket": _serialize_ticket(ticket), "idempotent": False}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Workflow trigger — starts the multi-agent LangGraph pipeline
# ---------------------------------------------------------------------------


@app.post("/tickets/{ticket_id}/process")
async def process_ticket(ticket_id: str, body: ProcessRequest):
    """
    Kick off automated ticket resolution.

    Creates (or reuses) a workflow run, then either:
      - publishes a job to the message queue for graph_worker (async_mode=True), or
      - invokes GraphRunner directly in this process (async_mode=False).
    """
    session = SessionLocal()
    try:
        ticket_repo = TicketRepository(session)
        workflow_repo = WorkflowRepository(session)
        ticket = ticket_repo.get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Avoid duplicate runs — resume an in-flight run if one already exists.
        active = workflow_repo.get_active_run(ticket.id)
        if active:
            run = active
        else:
            run = workflow_repo.create_run(ticket.id, ticket.tenant_id, settings.prompt_version)

        ticket_repo.update_from_state(ticket.id, {"status": "queued"})

        # Job payload is consumed by graph_worker / GraphRunner.
        # thread_id ({ticket_id}:{run_id}) keys LangGraph Redis checkpoints.
        job = {
            "ticket_id": ticket.id,
            "tenant_id": ticket.tenant_id,
            "title": ticket.title,
            "description": ticket.description,
            "user_id": ticket.user_id,
            "source": ticket.source,
            "run_id": run.id,
            "thread_id": run.thread_id,
            "prompt_version": settings.prompt_version,
        }

        if body.async_mode:
            await queue.publish(TicketJob.from_dict(job))
            return {"message": "Ticket queued for processing", "run_id": run.id, "thread_id": run.thread_id}

        from resolveops_core.graph.runner import GraphRunner

        result = GraphRunner().run(job)
        return result
    finally:
        session.close()


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Return ticket details plus all workflow runs for that ticket."""
    session = SessionLocal()
    try:
        ticket = TicketRepository(session).get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        runs = WorkflowRepository(session).list_runs_for_ticket(ticket_id)
        return {
            "ticket": _serialize_ticket(ticket),
            "runs": [_serialize_run(r) for r in runs],
        }
    finally:
        session.close()


@app.get("/tickets")
async def list_tickets(tenant_id: str | None = None, user_id: str | None = None):
    session = SessionLocal()
    try:
        tickets = TicketRepository(session).list_tickets(tenant_id=tenant_id, user_id=user_id)
        return {"tickets": [_serialize_ticket(t) for t in tickets]}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Workflow observability — audit trail and live LangGraph state
# ---------------------------------------------------------------------------


@app.get("/runs/{run_id}/events")
async def list_run_events(run_id: str):
    """Agent step audit log (state_before / state_patch / state_after per node)."""
    session = SessionLocal()
    try:
        events = WorkflowRepository(session).list_events(run_id)
        return {"events": [_serialize_event(e) for e in events]}
    finally:
        session.close()


@app.post("/runs/{thread_id}/resume")
async def resume_run(thread_id: str, body: HumanFeedbackRequest):
    """
    Human-in-the-loop resume.

    Called when a ticket was escalated and paused before human_review.
    Injects analyst feedback into the Redis checkpoint and continues the graph.
    """
    from resolveops_core.graph.runner import GraphRunner

    return GraphRunner().resume_human_review(thread_id, body.feedback)


@app.get("/state/threads/{thread_id}")
async def get_thread_state(thread_id: str):
    """Inspect live LangGraph checkpoint: current state, version, pending next steps."""
    from resolveops_core.graph.runner import GraphRunner

    session = SessionLocal()
    try:
        run = WorkflowRepository(session).get_run_by_thread(thread_id)
        if not run:
            raise HTTPException(status_code=404, detail="Thread not found")
        state_view = GraphRunner().get_state(thread_id)
        return {"run": _serialize_run(run), **state_view}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Admin UI — resolution metrics and recent activity
# ---------------------------------------------------------------------------


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    session = SessionLocal()
    try:
        tickets = TicketRepository(session).list_tickets(limit=20)
        runs = []
        for ticket in tickets:
            runs.extend(WorkflowRepository(session).list_runs_for_ticket(ticket.id))
        evaluator = EvaluationFramework()
        evaluations = [evaluator.evaluate_ticket(t).__dict__ for t in tickets]
        summary = evaluator.summarize(
            [evaluator.evaluate_ticket(t) for t in tickets]
        )
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "tickets": tickets,
                "runs": runs[:20],
                "evaluations": evaluations,
                "summary": summary,
            },
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# External ticketing integrations — pull tickets into ResolveOps
# ---------------------------------------------------------------------------


@app.post("/integrations/servicenow/import/{ticket_number}")
async def import_servicenow(ticket_number: str):
    """Fetch a ServiceNow incident and store it locally (mock mode when unconfigured)."""
    client = ServiceNowClient()
    data = client.get_ticket(ticket_number)
    session = SessionLocal()
    try:
        ticket = TicketRepository(session).create_ticket(data)
        return {"ticket": _serialize_ticket(ticket)}
    finally:
        session.close()


@app.post("/integrations/jira/import/{issue_key}")
async def import_jira(issue_key: str):
    """Fetch a Jira issue and store it locally (mock mode when unconfigured)."""
    client = JiraClient()
    data = client.get_ticket(issue_key)
    session = SessionLocal()
    try:
        ticket = TicketRepository(session).create_ticket(data)
        return {"ticket": _serialize_ticket(ticket)}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Serializers — map SQLAlchemy models to JSON-safe dicts for API responses
# ---------------------------------------------------------------------------


def _serialize_ticket(ticket):
    return {
        "id": ticket.id,
        "tenant_id": ticket.tenant_id,
        "title": ticket.title,
        "description": ticket.description,
        "user_id": ticket.user_id,
        "source": ticket.source,
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category,
        "ticket_type": ticket.ticket_type,
        "diagnosis": ticket.diagnosis,
        "resolution": ticket.resolution,
        "user_response": ticket.user_response,
        "confidence": ticket.confidence,
        "escalated": ticket.escalated,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }


def _serialize_run(run):
    return {
        "id": run.id,
        "ticket_id": run.ticket_id,
        "thread_id": run.thread_id,
        "status": run.status,
        "current_step": run.current_step,
        "state_version": run.state_version,
        "prompt_version": run.prompt_version,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error": run.error,
    }


def _serialize_event(event):
    return {
        "id": event.id,
        "run_id": event.run_id,
        "ticket_id": event.ticket_id,
        "agent_name": event.agent_name,
        "event_type": event.event_type,
        "payload": event.payload,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
