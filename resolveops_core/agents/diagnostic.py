from resolveops_core.agents.base import invoke_structured, maybe_llm_summarize
from resolveops_core.graph.state import TicketState
from resolveops_core.prompts.loader import load_prompt


def run_diagnostic(state: TicketState, prompt_version: str = "v1") -> dict:
    prompt = load_prompt("diagnostic", prompt_version)
    ctx = invoke_structured(prompt, state)
    text = ctx["text"]
    kb = " ".join(state.get("kb_context", [])).lower()
    tool_results = state.get("tool_results", [])

    if "vpn" in text or "vpn" in kb:
        diagnosis = "Likely stale VPN profile or expired MFA token."
        confidence = 0.82
    elif "password" in text or "locked" in text:
        diagnosis = "Account lockout due to failed login attempts."
        confidence = 0.9
    elif any(r.get("tool") == "check_service_health" and not r.get("healthy") for r in tool_results):
        diagnosis = "Dependent service is unhealthy."
        confidence = 0.75
    else:
        diagnosis = maybe_llm_summarize(prompt, state) or "Insufficient evidence for automated diagnosis."
        confidence = 0.45

    return {"diagnosis": diagnosis, "confidence": confidence, "status": "diagnosing"}
