import json

from resolveops_core.graph.nodes import _persist_step
from resolveops_core.graph.runner import GraphRunner
from resolveops_core.graph.state import initial_state


def _configure_test_logging(monkeypatch):
    import resolveops_core.logging as logging_module
    import resolveops_core.telemetry.tracing as tracing_module

    monkeypatch.setattr(tracing_module.settings, "otel_enabled", False)
    monkeypatch.setattr(tracing_module.settings, "otel_logs_enabled", False)
    tracing_module._CONFIGURED = False
    logging_module.configure_logging("INFO", service_name="resolveops-test")


def _mock_persist_db(monkeypatch):
    class FakeSession:
        def close(self):
            pass

    class FakeStore:
        def sync_after_step(self, *args, **kwargs):
            return None

    monkeypatch.setattr("resolveops_core.graph.nodes.SessionLocal", lambda: FakeSession())
    monkeypatch.setattr("resolveops_core.graph.nodes.StateStore", lambda *args, **kwargs: FakeStore())


def test_persist_step_logs_sanitized_patch(monkeypatch, capsys):
    _configure_test_logging(monkeypatch)
    _mock_persist_db(monkeypatch)

    state = initial_state(
        {
            "ticket_id": "INC-1",
            "title": "VPN issue",
            "description": "Error 619",
            "user_id": "jsmith",
            "run_id": "run-abc",
            "thread_id": "INC-1:run-abc",
        }
    )
    _persist_step(
        "triage",
        state,
        {
            "priority": "P2",
            "category": "Access/Identity",
            "status": "triaged",
            "messages": ["should-not-appear-raw"],
        },
    )

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["event"] == "graph.step"
    assert payload["agent"] == "triage"
    assert payload["run_id"] == "run-abc"
    assert payload["patch"]["priority"] == "P2"
    assert payload["patch"]["messages"] == "<1 message(s)>"


def test_invoke_fresh_logs_initial_state(monkeypatch, capsys):
    _configure_test_logging(monkeypatch)

    runner = GraphRunner(with_checkpoint=False)
    seed = initial_state(
        {
            "ticket_id": "INC-2",
            "title": "Password reset",
            "description": "Locked out",
            "user_id": "jsmith",
            "run_id": "run-xyz",
            "thread_id": "INC-2:run-xyz",
        }
    )
    monkeypatch.setattr(runner.app, "invoke", lambda _seed, config: _seed)
    monkeypatch.setattr(runner, "_finalize", lambda result, config, store, run_id: result)

    runner._invoke_fresh(seed, {"configurable": {"thread_id": seed["thread_id"]}}, None, "run-xyz")

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["event"] == "graph.initial_state"
    assert payload["ticket_id"] == "INC-2"
    assert payload["state_version"] == 0
    assert payload["state"]["status"] == "new"
    assert payload["state"]["messages_count"] == 0


def test_invoke_from_checkpoint_logs_resume_state(monkeypatch, capsys):
    _configure_test_logging(monkeypatch)

    runner = GraphRunner(with_checkpoint=False)
    resume_state = initial_state(
        {
            "ticket_id": "INC-3",
            "title": "Resume me",
            "description": "Paused ticket",
            "user_id": "jsmith",
            "run_id": "run-resume",
            "thread_id": "INC-3:run-resume",
        }
    )
    resume_state["state_version"] = 4
    resume_state["status"] = "awaiting_human"
    resume_state["current_step"] = "human_review"

    class FakeSnapshot:
        values = resume_state

    config = {"configurable": {"thread_id": resume_state["thread_id"]}}
    monkeypatch.setattr(runner.app, "get_state", lambda _config: FakeSnapshot())
    monkeypatch.setattr(runner.app, "invoke", lambda _seed, config: resume_state)
    monkeypatch.setattr(runner, "_finalize", lambda result, config, store, run_id: result)

    runner._invoke_from_checkpoint(config, None, "run-resume")

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["event"] == "graph.resume_state"
    assert payload["state_version"] == 4
    assert payload["state"]["status"] == "awaiting_human"
    assert payload["state"]["current_step"] == "human_review"


def test_resume_human_review_logs_resume_state(monkeypatch, capsys):
    _configure_test_logging(monkeypatch)

    runner = GraphRunner(with_checkpoint=False)
    resume_state = initial_state(
        {
            "ticket_id": "INC-4",
            "title": "Human review",
            "description": "Needs guidance",
            "user_id": "jsmith",
            "run_id": "run-hr",
            "thread_id": "INC-4:run-hr",
        }
    )
    resume_state["state_version"] = 6
    resume_state["status"] = "diagnosing"
    resume_state["requires_human"] = False
    resume_state["human_feedback"] = "Try resetting MFA"

    class FakeSnapshot:
        values = resume_state
        next = ()

    config = {"configurable": {"thread_id": resume_state["thread_id"]}}
    monkeypatch.setattr(runner.app, "get_state", lambda _config: FakeSnapshot())
    monkeypatch.setattr(runner.app, "update_state", lambda _config, _patch: None)
    monkeypatch.setattr(runner.app, "invoke", lambda _seed, config: resume_state)
    monkeypatch.setattr(
        runner,
        "_store",
        lambda: (FakeSession(), None),
    )
    monkeypatch.setattr(runner, "_finalize", lambda result, config, store, run_id: result)

    class FakeRun:
        id = "run-hr"
        ticket_id = "INC-4"

    class FakeWorkflowRepo:
        def get_run_by_thread(self, thread_id):
            return FakeRun()

    class FakeTicketRepo:
        def get_ticket(self, ticket_id):
            return None

    class FakeSession:
        def close(self):
            pass

    monkeypatch.setattr(
        "resolveops_core.graph.runner.WorkflowRepository",
        lambda session: FakeWorkflowRepo(),
    )
    monkeypatch.setattr(
        "resolveops_core.graph.runner.TicketRepository",
        lambda session: FakeTicketRepo(),
    )
    monkeypatch.setattr("resolveops_core.graph.runner.SessionLocal", lambda: FakeSession())

    runner.resume_human_review(resume_state["thread_id"], "Try resetting MFA")

    output = capsys.readouterr().out
    payload = json.loads(output.strip())
    assert payload["event"] == "graph.resume_state"
    assert payload["state_version"] == 6
    assert payload["state"]["human_feedback_provided"] is True
    assert "Try resetting MFA" not in output
