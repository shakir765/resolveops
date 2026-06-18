import { statusBadgeClass, statusLabel } from "../lib/status";

export function StatusBadge({ status }: { status: string }) {
  return <span className={statusBadgeClass(status)}>{statusLabel(status)}</span>;
}
