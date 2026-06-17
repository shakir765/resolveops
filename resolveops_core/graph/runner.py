from __future__ import annotations

from typing import Any

from resolveops_core.db.models import SessionLocal, init_db
from resolveops_core.db.repository import TicketRepository, WorkflowRepository
from resolveops_core.evaluation.metrics import EvaluationFramework
from resolveops_core.graph.state import graph_config, initial_state, snapshot_for_audit
from resolveops_core.graph.state_store import StateStore
from resolveops_core.graph.workflow import compile_workflow
from resolveops_core.logging import get_logger

logger = get_logger(__name__)


class GraphRunner:
    def __init__(self, with_checkpoint: bool = True):
        self.app = compile_workflow(with_checkpoint=with_checkpoint)
        self.with_checkpoint = with_checkpoint
        self.evaluator = EvaluationFramework()

    def _store(self) -> tuple[Any, StateStore]:
        session = SessionLocal()
        ticket_repo = TicketRepository(session)
        workflow_repo = WorkflowRepository(session)
        return session, StateStore(ticket_repo, workflow_repo)

    def _existing_checkpoint(self, thread_id: str) -> bool:
        if not self.with_checkpoint:
            return False
        snapshot = self.app.get_state(graph_config(thread_id))
        return bool(snapshot.values)

    def run(self, payload: dict) -> dict:
        init_db()
        session, store = self._store()
        ticket_repo = TicketRepository(session)
        workflow_repo = WorkflowRepository(session)

        ticket_id = payload["ticket_id"]
        tenant_id = payload.get("tenant_id", "default")
        run_id = payload.get("run_id")
        thread_id = payload.get("thread_id")

        try:
            if not run_id or not thread_id:
                run = workflow_repo.create_run(ticket_id, tenant_id, payload.get("prompt_version", "v1"))
                run_id = run.id
                thread_id = run.thread_id

            config = graph_config(thread_id)
            has_checkpoint = self._existing_checkpoint(thread_id)

            if has_checkpoint:
                logger.info("graph.resume_checkpoint", ticket_id=ticket_id, thread_id=thread_id)
                result = self._invoke_from_checkpoint(config, store, run_id)
            else:
                workflow_repo.mark_started(run_id)
                ticket_repo.update_from_state(ticket_id, {"status": "processing"})
                seed = initial_state({**payload, "run_id": run_id, "thread_id": thread_id})
                result = self._invoke_fresh(seed, config, store, run_id)

            return self._build_response(ticket_id, run_id, thread_id, result, ticket_repo, workflow_repo)
        except Exception as exc:
            if run_id:
                store.sync_run_failure(run_id, ticket_id, str(exc))
            logger.error("graph.failed", ticket_id=ticket_id, error=str(exc))
            raise
        finally:
            session.close()

    def _invoke_fresh(self, seed: dict, config: dict, store: StateStore, run_id: str) -> dict:
        result = self.app.invoke(seed, config=config)
        return self._finalize(result, config, store, run_id)

    def _invoke_from_checkpoint(self, config: dict, store: StateStore, run_id: str) -> dict:
        result = self.app.invoke(None, config=config)
        return self._finalize(result, config, store, run_id)

    def _finalize(self, result: dict, config: dict, store: StateStore, run_id: str) -> dict:
        snapshot = self.app.get_state(config)
        if snapshot.next:
            state = snapshot.values or result
            store.sync_interrupt(run_id, state, snapshot.next)
            state = {**state, "status": state.get("status") or "awaiting_human", "requires_human": True}
            return state
        store.sync_run_completion(run_id, result)
        return result

    def _build_response(self, ticket_id, run_id, thread_id, result, ticket_repo, workflow_repo) -> dict:
        ticket = ticket_repo.get_ticket(ticket_id)
        evaluation = self.evaluator.evaluate_ticket(ticket, result) if ticket else None
        snapshot = self.app.get_state(graph_config(thread_id))
        interrupted = bool(snapshot.next)

        logger.info(
            "graph.completed",
            ticket_id=ticket_id,
            status=result.get("status"),
            interrupted=interrupted,
            state_version=result.get("state_version"),
        )
        return {
            "ticket_id": ticket_id,
            "run_id": run_id,
            "thread_id": thread_id,
            "interrupted": interrupted,
            "next_steps": [str(s) for s in snapshot.next] if snapshot.next else [],
            "state": result,
            "state_snapshot": snapshot_for_audit(result),
            "evaluation": evaluation.__dict__ if evaluation else None,
        }

    def get_state(self, thread_id: str) -> dict:
        config = graph_config(thread_id)
        snapshot = self.app.get_state(config)
        values = snapshot.values or {}
        return {
            "thread_id": thread_id,
            "state": values,
            "state_snapshot": snapshot_for_audit(values) if values else {},
            "next_steps": [str(s) for s in snapshot.next] if snapshot.next else [],
            "state_version": values.get("state_version"),
            "current_step": values.get("current_step"),
        }

    def resume_human_review(self, thread_id: str, human_feedback: str) -> dict:
        session, store = self._store()
        try:
            workflow_repo = WorkflowRepository(session)
            run = workflow_repo.get_run_by_thread(thread_id)
            if not run:
                raise ValueError(f"No workflow run for thread_id={thread_id}")

            config = graph_config(thread_id)
            self.app.update_state(
                config,
                {
                    "human_feedback": human_feedback,
                    "requires_human": False,
                    "status": "diagnosing",
                },
            )
            result = self.app.invoke(None, config=config)
            result = self._finalize(result, config, store, run.id)
            ticket = TicketRepository(session).get_ticket(run.ticket_id)
            evaluation = self.evaluator.evaluate_ticket(ticket, result) if ticket else None
            snapshot = self.app.get_state(config)
            return {
                "thread_id": thread_id,
                "run_id": run.id,
                "interrupted": bool(snapshot.next),
                "next_steps": [str(s) for s in snapshot.next] if snapshot.next else [],
                "state": result,
                "state_snapshot": snapshot_for_audit(result),
                "evaluation": evaluation.__dict__ if evaluation else None,
            }
        finally:
            session.close()
