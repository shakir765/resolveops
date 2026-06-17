from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from resolveops_core.db.models import Ticket, TicketStatus, sla_deadline_for_priority


@dataclass
class EvaluationResult:
    ticket_id: str
    resolved: bool
    escalated: bool
    confidence: float
    sla_met: bool
    category: str | None
    score: float


class EvaluationFramework:
    def evaluate_ticket(self, ticket: Ticket, final_state: dict[str, Any] | None = None) -> EvaluationResult:
        state = final_state or {}
        status = state.get("status", ticket.status)
        priority = state.get("priority", ticket.priority) or "P3"
        confidence = float(state.get("confidence", ticket.confidence or 0.0))
        escalated = bool(state.get("escalated", ticket.escalated))
        resolved = status in {TicketStatus.RESOLVED.value, "validated", "closed"}
        completed_at = datetime.now(timezone.utc)
        deadline = sla_deadline_for_priority(priority)
        sla_met = completed_at <= deadline

        score = 0.0
        if resolved:
            score += 0.5
        if not escalated:
            score += 0.2
        if confidence >= 0.7:
            score += 0.2
        if sla_met:
            score += 0.1

        return EvaluationResult(
            ticket_id=ticket.id,
            resolved=resolved,
            escalated=escalated,
            confidence=confidence,
            sla_met=sla_met,
            category=state.get("category", ticket.category),
            score=round(score, 2),
        )

    def summarize(self, results: list[EvaluationResult]) -> dict[str, Any]:
        total = len(results) or 1
        return {
            "total": len(results),
            "resolution_rate": round(sum(1 for r in results if r.resolved) / total, 2),
            "escalation_rate": round(sum(1 for r in results if r.escalated) / total, 2),
            "avg_confidence": round(sum(r.confidence for r in results) / total, 2),
            "sla_met_rate": round(sum(1 for r in results if r.sla_met) / total, 2),
            "avg_score": round(sum(r.score for r in results) / total, 2),
        }
