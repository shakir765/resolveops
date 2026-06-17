from resolveops_core.agents.base import invoke_structured
from resolveops_core.db.models import sla_deadline_for_priority
from resolveops_core.graph.state import TicketState
from resolveops_core.prompts.loader import load_prompt


def run_triage(state: TicketState, prompt_version: str = "v1") -> dict:
    prompt = load_prompt("triage", prompt_version)
    ctx = invoke_structured(prompt, state)
    text = ctx["text"]

    if any(k in text for k in ("outage", "down", "cannot access", "production")):
        priority, category = "P1", "Infrastructure"
    elif any(k in text for k in ("vpn", "password", "login", "locked")):
        priority, category = "P2", "Access/Identity"
    elif any(k in text for k in ("install", "request", "new laptop")):
        priority, category = "P3", "Service Request"
    else:
        priority, category = "P3", "General IT"

    return {
        "priority": priority,
        "category": category,
        "status": "triaged",
        "sla_deadline": sla_deadline_for_priority(priority).isoformat(),
    }
