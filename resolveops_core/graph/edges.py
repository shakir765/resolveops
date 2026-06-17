from resolveops_core.graph.state import TicketState


def route_after_diagnostic(state: TicketState) -> str:
    if state.get("confidence", 0) < 0.7 or state.get("requires_human"):
        return "escalation"
    return "resolution"


def route_after_validator(state: TicketState) -> str:
    if state.get("status") == "validated":
        return "communication"
    if state.get("requires_human"):
        return "escalation"
    return "diagnostic"


def route_after_escalation(state: TicketState) -> str:
    # Always route to human_review; interrupt_before pauses before that node runs.
    if state.get("escalated") or state.get("requires_human"):
        return "human_review"
    return "end"
