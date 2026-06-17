from resolveops_core.agents.base import invoke_structured
from resolveops_core.graph.state import TicketState
from resolveops_core.prompts.loader import load_prompt


def run_resolution(state: TicketState, prompt_version: str = "v1") -> dict:
    prompt = load_prompt("resolution", prompt_version)
    ctx = invoke_structured(prompt, state)
    text = ctx["text"]
    diagnosis = (state.get("diagnosis") or "").lower()

    existing = set(state.get("actions_taken") or [])
    if "vpn" in text or "vpn" in diagnosis:
        plan = "1) Check VPN gateway health\n2) Reset VPN profile\n3) Reissue MFA token\n4) Confirm connectivity"
        actions = ["check_service_health", "reset_vpn_profile"]
    elif "password" in text or "locked" in text or "lockout" in diagnosis:
        plan = "1) Verify user identity\n2) Unlock account\n3) Reset password\n4) Notify user"
        actions = ["unlock_account", "reset_password"]
    else:
        plan = "Gather additional logs and escalate if issue persists."
        actions = ["lookup_asset"]

    new_actions = [action for action in actions if action not in existing]
    return {"resolution_plan": plan, "actions_taken": new_actions, "status": "resolving"}
