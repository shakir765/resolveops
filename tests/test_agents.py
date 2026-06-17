import json
from pathlib import Path

import pytest

from resolveops_core.agents.diagnostic import run_diagnostic
from resolveops_core.agents.triage import run_triage
from resolveops_core.graph.state import initial_state
from resolveops_core.graph.workflow import compile_workflow
from resolveops_core.evaluation.metrics import EvaluationFramework
from resolveops_core.tools.registry import execute_tool


FIXTURES = Path(__file__).parent / "fixtures" / "sample_tickets.json"


@pytest.fixture
def sample_tickets():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_triage_vpn_ticket(sample_tickets):
    state = initial_state(sample_tickets[0])
    result = run_triage(state)
    assert result["priority"] == "P2"
    assert result["category"] == "Access/Identity"


def test_diagnostic_password_ticket(sample_tickets):
    state = initial_state(sample_tickets[1])
    state.update({"kb_context": ["Account lockout runbook"]})
    result = run_diagnostic(state)
    assert result["confidence"] >= 0.7
    assert "lockout" in result["diagnosis"].lower()


def test_tool_registry_reset_password():
    result = execute_tool("reset_password", {"user_id": "jsmith", "ticket_id": "INC-1"})
    assert result["success"] is True
    assert result["tool"] == "reset_password"


def test_graph_vpn_path_without_checkpoint(sample_tickets, monkeypatch):
    monkeypatch.setattr(
        "resolveops_core.agents.knowledge.run_knowledge",
        lambda state: {"kb_context": ["VPN Error 619: reset VPN profile"]},
    )
    monkeypatch.setattr(
        "resolveops_core.agents.tool_executor.run_tool_executor",
        lambda state: {
            "tool_results": [
                {"tool": "check_service_health", "success": True, "healthy": True},
                {"tool": "reset_vpn_profile", "success": True},
            ],
            "status": "executing",
        },
    )

    app = compile_workflow(with_checkpoint=False)
    state = initial_state(sample_tickets[0])
    result = app.invoke(state)
    assert result["status"] in {"resolved", "validated", "escalated", "awaiting_human"}
    assert result.get("diagnosis")


def test_evaluation_framework():
    class Ticket:
        id = "INC-1"
        status = "resolved"
        priority = "P2"
        category = "Access/Identity"
        confidence = 0.85
        escalated = False

    result = EvaluationFramework().evaluate_ticket(Ticket())
    assert result.resolved is True
    assert result.score > 0.5
