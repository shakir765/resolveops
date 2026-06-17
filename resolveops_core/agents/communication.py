from resolveops_core.agents.base import maybe_llm_summarize
from resolveops_core.graph.state import TicketState
from resolveops_core.prompts.loader import load_prompt


def run_communication(state: TicketState, prompt_version: str = "v1") -> dict:
    prompt = load_prompt("communication", prompt_version)

    if state.get("escalated"):
        return {"user_response": state.get("user_response"), "status": "escalated"}

    summary = (
        f"We resolved your issue related to {state.get('category', 'IT support')}.\n"
        f"Diagnosis: {state.get('diagnosis')}\n"
        f"Actions: {', '.join(state.get('actions_taken', []))}\n"
        f"Resolution plan: {state.get('resolution_plan')}"
    )
    response = maybe_llm_summarize(prompt, {**state, "description": summary})
    return {"user_response": response or summary, "status": "resolved"}
