import pytest

from resolveops_core.graph.state import (
    AGENT_WRITE_KEYS,
    apply_agent_patch,
    build_thread_id,
    initial_state,
    merge_tool_results,
    next_state_version,
    parse_thread_id,
    snapshot_for_audit,
)


def test_build_and_parse_thread_id():
    thread_id = build_thread_id("INC-10482", "run-abc123")
    assert thread_id == "INC-10482:run-abc123"
    ticket_id, run_id = parse_thread_id(thread_id)
    assert ticket_id == "INC-10482"
    assert run_id == "run-abc123"


def test_reducers_append_lists():
    first = [{"tool": "reset_password", "success": True}]
    second = [{"tool": "unlock_account", "success": True}]
    merged = merge_tool_results(first, second)
    assert len(merged) == 2
    assert merged[0]["tool"] == "reset_password"


def test_agent_patch_ownership():
    state = initial_state(
        {
            "ticket_id": "INC-1",
            "title": "VPN issue",
            "description": "Error 619",
            "user_id": "jsmith",
        }
    )
    raw = {
        "priority": "P2",
        "category": "Access/Identity",
        "status": "triaged",
        "ticket_id": "SHOULD-NOT-OVERWRITE",
    }
    patch = apply_agent_patch("triage", raw)
    assert patch["priority"] == "P2"
    assert "ticket_id" not in patch


def test_state_version_increments():
    state = initial_state(
        {
            "ticket_id": "INC-1",
            "title": "t",
            "description": "d",
            "user_id": "u",
        }
    )
    state["state_version"] = 3
    assert next_state_version(state) == 4


def test_snapshot_for_audit_redacts_messages():
    state = initial_state(
        {
            "ticket_id": "INC-1",
            "title": "t",
            "description": "d",
            "user_id": "u",
            "human_feedback": "secret guidance",
        }
    )
    state["messages"] = ["msg1", "msg2"]
    state["kb_context"] = ["chunk1"]
    snap = snapshot_for_audit(state)
    assert snap["messages_count"] == 2
    assert snap["kb_context_count"] == 1
    assert snap["human_feedback_provided"] is True
    assert "secret" not in str(snap)


def test_all_agents_have_write_keys():
    expected = {
        "supervisor",
        "triage",
        "classifier",
        "knowledge",
        "diagnostic",
        "resolution",
        "tool_executor",
        "validator",
        "escalation",
        "human_review",
        "communication",
    }
    assert set(AGENT_WRITE_KEYS) == expected
