from resolveops_core.graph.state import TicketState


def run_validator(state: TicketState) -> dict:
    tool_results = state.get("tool_results", [])
    confidence = state.get("confidence", 0.0)
    failed = [r for r in tool_results if not r.get("success", False)]

    if failed:
        return {
            "status": "diagnosing",
            "confidence": max(0.0, confidence - 0.2),
            "requires_human": confidence < 0.5,
        }

    if confidence >= 0.7 and state.get("resolution_plan"):
        return {"status": "validated", "confidence": confidence}

    return {"status": "diagnosing", "requires_human": True}
