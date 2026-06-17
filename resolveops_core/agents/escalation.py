from resolveops_core.graph.state import TicketState


def run_escalation(state: TicketState) -> dict:
    return {
        "escalated": True,
        "requires_human": True,
        "status": "awaiting_human",
        "user_response": (
            "Your ticket has been escalated to a human analyst for further investigation. "
            f"Reference: {state['ticket_id']}"
        ),
    }
