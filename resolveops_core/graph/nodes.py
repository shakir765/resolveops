from __future__ import annotations

from langchain_core.messages import AIMessage

from resolveops_core.agents.classifier import run_classifier
from resolveops_core.agents.communication import run_communication
from resolveops_core.agents.diagnostic import run_diagnostic
from resolveops_core.agents.escalation import run_escalation
from resolveops_core.agents.knowledge import run_knowledge
from resolveops_core.agents.resolution import run_resolution
from resolveops_core.agents.supervisor import run_supervisor
from resolveops_core.agents.tool_executor import run_tool_executor
from resolveops_core.agents.triage import run_triage
from resolveops_core.agents.validator import run_validator
from resolveops_core.config import settings
from resolveops_core.db.models import SessionLocal
from resolveops_core.db.repository import TicketRepository, WorkflowRepository
from resolveops_core.graph.state import (
    TicketState,
    apply_agent_patch,
    next_state_version,
    sanitize_patch_for_log,
)
from resolveops_core.graph.state_store import StateStore
from resolveops_core.logging import get_logger
from resolveops_core.telemetry import get_tracer

logger = get_logger(__name__)


def _tracer():
    return get_tracer(__name__)

PROMPT_AGENTS = frozenset({"triage", "classifier", "diagnostic", "resolution", "communication"})


def _build_patch(agent_name: str, state: TicketState, raw_patch: dict) -> dict:
    patch = apply_agent_patch(agent_name, raw_patch)
    patch["current_step"] = agent_name
    patch["state_version"] = next_state_version(state)

    summary = patch.get("diagnosis") or patch.get("resolution_plan") or patch.get("user_response")
    if summary:
        patch.setdefault("messages", [AIMessage(content=f"[{agent_name}] {str(summary)[:500]}")])

    return patch


def _persist_step(agent_name: str, state: TicketState, raw_patch: dict) -> dict:
    patch = _build_patch(agent_name, state, raw_patch)
    run_id = state.get("run_id", "")

    if not run_id:
        return patch

    session = SessionLocal()
    try:
        store = StateStore(TicketRepository(session), WorkflowRepository(session))
        state_after = {**state, **patch}
        store.sync_after_step(
            run_id,
            agent_name,
            state,
            sanitize_patch_for_log(patch),
            state_after,  # type: ignore[arg-type]
        )
    finally:
        session.close()

    logger.info(
        "graph.step",
        agent=agent_name,
        ticket_id=state.get("ticket_id"),
        state_version=patch.get("state_version"),
        status=patch.get("status", state.get("status")),
    )
    return patch


def make_node(agent_name: str, fn):
    def node(state: TicketState) -> dict:
        with _tracer().start_as_current_span(
            f"graph.node.{agent_name}",
            attributes={
                "graph.agent": agent_name,
                "ticket.id": state.get("ticket_id", ""),
                "run.id": state.get("run_id", ""),
            },
        ):
            prompt_version = settings.prompt_version
            if agent_name in PROMPT_AGENTS:
                raw = fn(state, prompt_version)
            else:
                raw = fn(state)
            return _persist_step(agent_name, state, raw)

    node.__name__ = agent_name
    return node


supervisor_node = make_node("supervisor", run_supervisor)
triage_node = make_node("triage", run_triage)
classifier_node = make_node("classifier", run_classifier)
knowledge_node = make_node("knowledge", run_knowledge)
diagnostic_node = make_node("diagnostic", run_diagnostic)
resolution_node = make_node("resolution", run_resolution)
tool_executor_node = make_node("tool_executor", run_tool_executor)
validator_node = make_node("validator", run_validator)
escalation_node = make_node("escalation", run_escalation)
communication_node = make_node("communication", run_communication)


def human_review_node(state: TicketState) -> dict:
    feedback = state.get("human_feedback")
    if feedback:
        raw = {
            "requires_human": False,
            "escalated": False,
            "status": "diagnosing",
            "resolution_plan": feedback,
        }
    else:
        raw = {"status": "awaiting_human", "requires_human": True}
    return _persist_step("human_review", state, raw)
