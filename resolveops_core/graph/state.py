"""LangGraph state schema, reducers, and lifecycle helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Reducers — list fields append; messages use LangGraph's add_messages
# ---------------------------------------------------------------------------


def merge_string_list(existing: list[str] | None, new: list[str] | None) -> list[str]:
    return (existing or []) + (new or [])


def merge_tool_results(
    existing: list[dict[str, Any]] | None,
    new: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    return (existing or []) + (new or [])


def merge_artifact_refs(
    existing: list[str] | None,
    new: list[str] | None,
) -> list[str]:
    return (existing or []) + (new or [])


def bump_state_version(existing: int | None, new: int | None) -> int:
    """Reducer: always take the higher version (nodes emit existing + 1)."""
    return max(existing or 0, new or 0)


# ---------------------------------------------------------------------------
# Agent write ownership — each agent may only patch its own keys
# ---------------------------------------------------------------------------

AGENT_WRITE_KEYS: dict[str, frozenset[str]] = {
    "supervisor": frozenset({"status", "current_step", "messages", "state_version"}),
    "triage": frozenset({"priority", "category", "status", "sla_deadline", "current_step", "messages", "state_version"}),
    "classifier": frozenset({"ticket_type", "current_step", "messages", "state_version"}),
    "knowledge": frozenset({"kb_context", "artifact_refs", "current_step", "messages", "state_version"}),
    "diagnostic": frozenset({"diagnosis", "confidence", "status", "current_step", "messages", "state_version"}),
    "resolution": frozenset({"resolution_plan", "actions_taken", "status", "current_step", "messages", "state_version"}),
    "tool_executor": frozenset({"tool_results", "status", "current_step", "messages", "state_version"}),
    "validator": frozenset({"status", "confidence", "requires_human", "current_step", "messages", "state_version"}),
    "escalation": frozenset({
        "escalated",
        "requires_human",
        "status",
        "user_response",
        "current_step",
        "messages",
        "state_version",
    }),
    "human_review": frozenset({
        "human_feedback",
        "requires_human",
        "escalated",
        "status",
        "resolution_plan",
        "current_step",
        "messages",
        "state_version",
    }),
    "communication": frozenset({"user_response", "status", "current_step", "messages", "state_version"}),
}

IMMUTABLE_INPUT_KEYS = frozenset({
    "ticket_id",
    "tenant_id",
    "correlation_id",
    "run_id",
    "thread_id",
    "title",
    "description",
    "user_id",
    "source",
})

SENSITIVE_KEYS = frozenset({"human_feedback"})  # never log raw values


class TicketState(TypedDict, total=False):
    # Identity (immutable after seed)
    ticket_id: str
    tenant_id: str
    correlation_id: str
    run_id: str
    thread_id: str

    # Input
    title: str
    description: str
    user_id: str
    source: str

    # Workflow outputs — filled incrementally by agents
    priority: Optional[str]
    category: Optional[str]
    ticket_type: Optional[str]
    kb_context: Annotated[list[str], merge_string_list]
    diagnosis: Optional[str]
    resolution_plan: Optional[str]
    tool_results: Annotated[list[dict[str, Any]], merge_tool_results]
    user_response: Optional[str]
    artifact_refs: Annotated[list[str], merge_artifact_refs]

    # Control plane
    status: str                   # business ticket status
    current_step: str             # graph node position
    confidence: float
    escalated: bool
    requires_human: bool
    human_feedback: Optional[str]
    error: Optional[str]
    sla_deadline: Optional[str]
    actions_taken: Annotated[list[str], merge_string_list]
    state_version: Annotated[int, bump_state_version]

    # Agent conversation history
    messages: Annotated[list, add_messages]


def build_thread_id(ticket_id: str, run_id: str) -> str:
    return f"{ticket_id}:{run_id}"


def parse_thread_id(thread_id: str) -> tuple[str, str]:
    ticket_id, _, run_id = thread_id.partition(":")
    if not run_id:
        raise ValueError(f"Invalid thread_id format: {thread_id}")
    return ticket_id, run_id


def initial_state(payload: dict[str, Any]) -> TicketState:
    run_id = payload.get("run_id", "")
    ticket_id = payload["ticket_id"]
    thread_id = payload.get("thread_id") or (build_thread_id(ticket_id, run_id) if run_id else "")

    return TicketState(
        ticket_id=ticket_id,
        tenant_id=payload.get("tenant_id", "default"),
        correlation_id=payload.get("correlation_id", ticket_id),
        run_id=run_id,
        thread_id=thread_id,
        title=payload["title"],
        description=payload["description"],
        user_id=payload["user_id"],
        source=payload.get("source", "api"),
        priority=None,
        category=None,
        ticket_type=None,
        kb_context=[],
        diagnosis=None,
        resolution_plan=None,
        tool_results=[],
        user_response=None,
        artifact_refs=[],
        status="new",
        current_step="supervisor",
        confidence=0.0,
        escalated=False,
        requires_human=False,
        human_feedback=None,
        error=None,
        sla_deadline=None,
        actions_taken=[],
        state_version=0,
        messages=[],
    )


def apply_agent_patch(agent_name: str, patch: dict[str, Any]) -> dict[str, Any]:
    """Restrict agent output to owned keys; block overwrites of immutable inputs."""
    allowed = AGENT_WRITE_KEYS.get(agent_name, frozenset())
    safe: dict[str, Any] = {}
    for key, value in patch.items():
        if key in IMMUTABLE_INPUT_KEYS:
            continue
        if key not in allowed:
            continue
        safe[key] = value
    return safe


def next_state_version(state: TicketState) -> int:
    return int(state.get("state_version") or 0) + 1


def snapshot_for_audit(state: TicketState) -> dict[str, Any]:
    """Lightweight, redacted snapshot for workflow_events (no secrets, no full messages)."""
    snap: dict[str, Any] = {}
    for key in (
        "ticket_id",
        "run_id",
        "thread_id",
        "status",
        "current_step",
        "priority",
        "category",
        "ticket_type",
        "diagnosis",
        "resolution_plan",
        "confidence",
        "escalated",
        "requires_human",
        "state_version",
        "sla_deadline",
    ):
        if key in state:
            snap[key] = state[key]
    snap["kb_context_count"] = len(state.get("kb_context") or [])
    snap["tool_results_count"] = len(state.get("tool_results") or [])
    snap["actions_taken"] = list(state.get("actions_taken") or [])
    snap["messages_count"] = len(state.get("messages") or [])
    if state.get("human_feedback"):
        snap["human_feedback_provided"] = True
    return snap


def sanitize_patch_for_log(patch: dict[str, Any]) -> dict[str, Any]:
    logged = dict(patch)
    for key in SENSITIVE_KEYS:
        if key in logged and logged[key]:
            logged[key] = "<redacted>"
    if "messages" in logged:
        logged["messages"] = f"<{len(logged['messages'])} message(s)>"
    return logged


def graph_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def is_terminal_status(status: str) -> bool:
    return status in {"resolved", "escalated", "closed", "failed", "completed"}


def run_status_from_state(state: TicketState) -> str:
    if state.get("requires_human") and state.get("status") == "awaiting_human":
        return "paused"
    if is_terminal_status(state.get("status", "")):
        return "completed"
    return "processing"
