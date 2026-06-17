import json
from pathlib import Path

from resolveops_core.rag.knowledge_base import KnowledgeBase


def main() -> None:
    docs = [
        {
            "id": "kb-vpn-619",
            "content": "VPN Error 619 troubleshooting: verify credentials, reset VPN profile, reissue MFA token, check VPN gateway health.",
            "source": "runbook",
        },
        {
            "id": "kb-account-lockout",
            "content": "Account lockout runbook: confirm user identity, unlock account in AD, reset password if policy requires, notify user.",
            "source": "runbook",
        },
        {
            "id": "kb-password-reset",
            "content": "Password reset procedure: validate requester, issue temporary password, require change at next login.",
            "source": "runbook",
        },
        {
            "id": "kb-service-health",
            "content": "Service health check: query monitoring API for VPN gateway, auth service, and DNS dependencies.",
            "source": "runbook",
        },
        {
            "id": "kb-past-ticket-991",
            "content": "Past ticket INC-991: VPN error 619 resolved by resetting VPN profile and MFA token for remote user.",
            "source": "past_ticket",
        },
    ]

    kb = KnowledgeBase()
    count = kb.ingest_documents(docs)
    output = {"ingested": count, "documents": [doc["id"] for doc in docs]}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
