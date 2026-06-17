from typing import Any, Optional

import httpx

from resolveops_core.config import settings
from resolveops_core.logging import get_logger

logger = get_logger(__name__)


class ServiceNowClient:
    def __init__(self):
        self.instance = settings.servicenow_instance
        self.username = settings.servicenow_username
        self.password = settings.servicenow_password

    @property
    def configured(self) -> bool:
        return bool(self.instance and self.username and self.password)

    def get_ticket(self, ticket_number: str) -> dict[str, Any]:
        if not self.configured:
            return self._mock_ticket(ticket_number, source="servicenow")
        url = f"https://{self.instance}/api/now/table/incident"
        with httpx.Client(auth=(self.username, self.password), timeout=20.0) as client:
            response = client.get(url, params={"sysparm_query": f"number={ticket_number}"})
            response.raise_for_status()
            records = response.json().get("result", [])
            if not records:
                raise ValueError(f"ServiceNow ticket not found: {ticket_number}")
            record = records[0]
            return {
                "ticket_id": record.get("number"),
                "title": record.get("short_description"),
                "description": record.get("description") or record.get("short_description"),
                "user_id": record.get("caller_id", {}).get("value", "unknown"),
                "source": "servicenow",
                "external_ref": record.get("sys_id"),
            }

    def update_ticket(self, ticket_number: str, comment: str, status: Optional[str] = None) -> dict[str, Any]:
        if not self.configured:
            logger.info("servicenow.mock_update", ticket=ticket_number, status=status)
            return {"success": True, "mock": True, "ticket_id": ticket_number, "comment": comment}
        url = f"https://{self.instance}/api/now/table/incident"
        payload: dict[str, Any] = {"work_notes": comment}
        if status:
            payload["state"] = status
        with httpx.Client(auth=(self.username, self.password), timeout=20.0) as client:
            response = client.patch(
                url,
                params={"sysparm_query": f"number={ticket_number}"},
                json=payload,
            )
            response.raise_for_status()
            return {"success": True, "ticket_id": ticket_number}

    def _mock_ticket(self, ticket_number: str, source: str) -> dict[str, Any]:
        return {
            "ticket_id": ticket_number,
            "title": "Imported ServiceNow ticket",
            "description": "Mock imported ticket for local development.",
            "user_id": "demo.user",
            "source": source,
            "external_ref": ticket_number,
        }


class JiraClient:
    def __init__(self):
        self.base_url = settings.jira_base_url.rstrip("/")
        self.email = settings.jira_email
        self.token = settings.jira_api_token

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.email and self.token)

    def get_ticket(self, issue_key: str) -> dict[str, Any]:
        if not self.configured:
            return {
                "ticket_id": issue_key,
                "title": "Imported Jira issue",
                "description": "Mock imported Jira issue for local development.",
                "user_id": "demo.user",
                "source": "jira",
                "external_ref": issue_key,
            }
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        with httpx.Client(auth=(self.email, self.token), timeout=20.0) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            fields = data.get("fields", {})
            return {
                "ticket_id": issue_key,
                "title": fields.get("summary"),
                "description": fields.get("description", {}).get("content", [{}])[0].get("content", [{}])[0].get(
                    "text", fields.get("summary")
                ),
                "user_id": fields.get("reporter", {}).get("accountId", "unknown"),
                "source": "jira",
                "external_ref": issue_key,
            }

    def add_comment(self, issue_key: str, comment: str) -> dict[str, Any]:
        if not self.configured:
            logger.info("jira.mock_comment", issue=issue_key)
            return {"success": True, "mock": True, "ticket_id": issue_key, "comment": comment}
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        payload = {"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]}}
        with httpx.Client(auth=(self.email, self.token), timeout=20.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return {"success": True, "ticket_id": issue_key}
