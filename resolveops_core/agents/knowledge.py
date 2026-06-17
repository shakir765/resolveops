import httpx

from resolveops_core.config import settings
from resolveops_core.graph.state import TicketState


def run_knowledge(state: TicketState) -> dict:
    query = f"{state['title']} {state['description']} {state.get('category', '')}"
    try:
        response = httpx.post(
            f"{settings.rag_service_url}/retrieve",
            json={"query": query, "top_k": 3},
            timeout=10.0,
        )
        response.raise_for_status()
        chunks = [item["content"] for item in response.json().get("results", [])]
    except Exception:
        chunks = _fallback_kb(state)

    return {"kb_context": chunks}


def _fallback_kb(state: TicketState) -> list[str]:
    text = f"{state['title']} {state['description']}".lower()
    if "vpn" in text:
        return [
            "VPN Error 619: reset VPN profile and verify MFA token.",
            "Check VPN gateway health before user-side resets.",
        ]
    if "password" in text or "locked" in text:
        return [
            "Account lockout runbook: verify failed attempts, unlock account, force password reset if needed.",
        ]
    return ["General troubleshooting: verify user identity, reproduce issue, check service health."]
