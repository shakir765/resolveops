export type TicketStatus =
  | "new"
  | "queued"
  | "processing"
  | "triaged"
  | "diagnosing"
  | "resolving"
  | "executing"
  | "validated"
  | "resolved"
  | "escalated"
  | "awaiting_human"
  | "closed"
  | "failed";

export interface Ticket {
  id: string;
  tenant_id: string;
  title: string;
  description: string;
  user_id: string;
  source: string;
  status: TicketStatus | string;
  priority: string | null;
  category: string | null;
  ticket_type: string | null;
  diagnosis: string | null;
  resolution: string | null;
  user_response: string | null;
  confidence: number | null;
  escalated: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface WorkflowRun {
  id: string;
  ticket_id: string;
  thread_id: string;
  status: string;
  current_step: string | null;
  state_version: number;
  prompt_version: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface TicketDetailResponse {
  ticket: Ticket;
  runs: WorkflowRun[];
}
