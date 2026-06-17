import httpx

from resolveops_core.config import settings
from resolveops_core.graph.state import TicketState


def run_tool_executor(state: TicketState) -> dict:
    executed_tools = {r.get("tool") for r in state.get("tool_results") or []}
    pending_actions = [a for a in state.get("actions_taken", []) if a not in executed_tools]
    user_id = state.get("user_id", "")
    results: list[dict] = []

    for action in pending_actions:
        try:
            response = httpx.post(
                f"{settings.tool_runner_url}/execute",
                json={"tool": action, "params": {"user_id": user_id, "ticket_id": state["ticket_id"]}},
                timeout=15.0,
            )
            response.raise_for_status()
            results.append(response.json())
        except Exception as exc:
            results.append({"tool": action, "success": False, "error": str(exc)})

    return {"tool_results": results, "status": "executing"}
