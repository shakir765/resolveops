from datetime import datetime, timezone
from typing import Any


def reset_password(user_id: str, ticket_id: str) -> dict[str, Any]:
    return {
        "tool": "reset_password",
        "success": True,
        "user_id": user_id,
        "ticket_id": ticket_id,
        "message": f"Temporary password reset initiated for {user_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def unlock_account(user_id: str, ticket_id: str) -> dict[str, Any]:
    return {
        "tool": "unlock_account",
        "success": True,
        "user_id": user_id,
        "ticket_id": ticket_id,
        "message": f"Account unlocked for {user_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def check_service_health(user_id: str, ticket_id: str) -> dict[str, Any]:
    healthy = "vpn" not in ticket_id.lower()
    return {
        "tool": "check_service_health",
        "success": True,
        "healthy": healthy,
        "service": "vpn-gateway",
        "ticket_id": ticket_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def reset_vpn_profile(user_id: str, ticket_id: str) -> dict[str, Any]:
    return {
        "tool": "reset_vpn_profile",
        "success": True,
        "user_id": user_id,
        "ticket_id": ticket_id,
        "message": f"VPN profile reset for {user_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def lookup_asset(user_id: str, ticket_id: str) -> dict[str, Any]:
    return {
        "tool": "lookup_asset",
        "success": True,
        "user_id": user_id,
        "asset_id": f"ASSET-{user_id[:4].upper()}",
        "model": "ThinkPad X1",
        "ticket_id": ticket_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def update_ticket(ticket_id: str, comment: str, status: str | None = None) -> dict[str, Any]:
    return {
        "tool": "update_ticket",
        "success": True,
        "ticket_id": ticket_id,
        "comment": comment,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


TOOL_REGISTRY = {
    "reset_password": reset_password,
    "unlock_account": unlock_account,
    "check_service_health": check_service_health,
    "reset_vpn_profile": reset_vpn_profile,
    "lookup_asset": lookup_asset,
    "update_ticket": update_ticket,
}


def execute_tool(tool: str, params: dict[str, Any]) -> dict[str, Any]:
    if tool not in TOOL_REGISTRY:
        return {"tool": tool, "success": False, "error": f"Unknown tool: {tool}"}
    fn = TOOL_REGISTRY[tool]
    if tool == "update_ticket":
        return fn(params.get("ticket_id", ""), params.get("comment", ""), params.get("status"))
    return fn(params.get("user_id", ""), params.get("ticket_id", ""))
