from resolveops_core.agents.base import invoke_structured
from resolveops_core.graph.state import TicketState
from resolveops_core.prompts.loader import load_prompt


def run_classifier(state: TicketState, prompt_version: str = "v1") -> dict:
    prompt = load_prompt("classifier", prompt_version)
    ctx = invoke_structured(prompt, state)
    text = ctx["text"]

    if any(k in text for k in ("install", "request access", "new laptop", "software request")):
        ticket_type = "request"
    elif any(k in text for k in ("recurring", "root cause", "pattern")):
        ticket_type = "problem"
    elif any(k in text for k in ("change window", "deploy", "upgrade")):
        ticket_type = "change"
    else:
        ticket_type = "incident"

    return {"ticket_type": ticket_type}
