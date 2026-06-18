export type DisplayStatus = "queued" | "in_progress" | "resolved" | "escalated" | "failed";

const IN_PROGRESS = new Set([
  "processing",
  "triaged",
  "diagnosing",
  "resolving",
  "executing",
  "validated",
]);

export function displayStatus(status: string): DisplayStatus {
  if (status === "new" || status === "queued") return "queued";
  if (IN_PROGRESS.has(status)) return "in_progress";
  if (status === "resolved" || status === "closed") return "resolved";
  if (status === "escalated" || status === "awaiting_human") return "escalated";
  if (status === "failed") return "failed";
  return "in_progress";
}

export function isTerminal(status: string): boolean {
  const d = displayStatus(status);
  return d === "resolved" || d === "failed" || d === "escalated";
}

export function statusLabel(status: string): string {
  const map: Record<DisplayStatus, string> = {
    queued: "Queued",
    in_progress: "In progress",
    resolved: "Resolved",
    escalated: "With analyst",
    failed: "Failed",
  };
  return map[displayStatus(status)];
}

export function statusBadgeClass(status: string): string {
  const base = "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium";
  switch (displayStatus(status)) {
    case "queued":
      return `${base} bg-slate-100 text-slate-700`;
    case "in_progress":
      return `${base} bg-blue-100 text-blue-800`;
    case "resolved":
      return `${base} bg-emerald-100 text-emerald-800`;
    case "escalated":
      return `${base} bg-violet-100 text-violet-800`;
    case "failed":
      return `${base} bg-red-100 text-red-800`;
    default:
      return `${base} bg-slate-100 text-slate-700`;
  }
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}
