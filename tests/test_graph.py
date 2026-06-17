import json
from pathlib import Path

import pytest

from resolveops_core.graph.state import initial_state
from resolveops_core.graph.workflow import compile_workflow


FIXTURES = Path(__file__).parent / "fixtures" / "sample_tickets.json"


@pytest.fixture
def sample_tickets():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_graph_escalation_path_for_vague_ticket(sample_tickets):
    app = compile_workflow(with_checkpoint=False)
    vague = {
        "ticket_id": "INC-99999",
        "title": "Something is wrong",
        "description": "App feels slow sometimes.",
        "user_id": "user1",
        "source": "api",
    }
    result = app.invoke(initial_state(vague))
    assert result["status"] in {"awaiting_human", "escalated", "resolved", "diagnosing"}
    assert result.get("confidence", 0) <= 0.7 or result.get("escalated") is True


def test_graph_password_resolution_path(sample_tickets, monkeypatch):
    monkeypatch.setattr(
        "resolveops_core.agents.tool_executor.run_tool_executor",
        lambda state: {
            "tool_results": [
                {"tool": "unlock_account", "success": True},
                {"tool": "reset_password", "success": True},
            ],
            "status": "executing",
        },
    )
    app = compile_workflow(with_checkpoint=False)
    result = app.invoke(initial_state(sample_tickets[1]))
    assert result.get("diagnosis")
    assert result["status"] in {"resolved", "validated", "escalated", "awaiting_human"}
