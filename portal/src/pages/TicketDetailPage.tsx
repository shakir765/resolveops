import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getTicket } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { displayStatus, formatDate, isTerminal } from "../lib/status";

export function TicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>();

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["ticket", ticketId],
    queryFn: () => getTicket(ticketId!),
    enabled: Boolean(ticketId),
    refetchInterval: (query) => {
      const status = query.state.data?.ticket.status ?? "";
      return isTerminal(status) ? false : 10_000;
    },
  });

  if (isLoading) {
    return <p className="text-slate-500">Loading ticket…</p>;
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
        Ticket not found or API unavailable.
      </div>
    );
  }

  const { ticket, runs } = data;
  const latestRun = runs[0];
  const terminal = isTerminal(ticket.status);
  const showResolution = Boolean(ticket.user_response) && displayStatus(ticket.status) !== "queued";

  return (
    <div className="space-y-6">
      <Link to="/tickets" className="text-sm font-medium text-blue-600 hover:underline">
        ← Back to my tickets
      </Link>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-mono text-sm text-slate-500">{ticket.id}</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">{ticket.title}</h1>
          <p className="mt-2 text-sm text-slate-500">
            Submitted {formatDate(ticket.created_at)}
            {ticket.category ? ` · ${ticket.category}` : ""}
            {ticket.priority ? ` · ${ticket.priority}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={ticket.status} />
          {!terminal && isFetching && (
            <span className="text-xs text-slate-500">Updating…</span>
          )}
        </div>
      </div>

      {!terminal && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-6">
          <h2 className="font-medium text-blue-900">In progress</h2>
          <p className="mt-2 text-sm text-blue-800">
            We are investigating your request. This page refreshes automatically every few
            seconds.
          </p>
          <ol className="mt-4 flex flex-wrap gap-2 text-xs text-blue-800">
            {["Received", "Investigating", "Resolution"].map((step, i) => (
              <li
                key={step}
                className={`rounded-full px-3 py-1 ${
                  i === 0 || displayStatus(ticket.status) !== "queued"
                    ? "bg-blue-200 font-medium"
                    : "bg-blue-100"
                }`}
              >
                {step}
              </li>
            ))}
          </ol>
        </div>
      )}

      {showResolution && (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Resolution for you
          </h2>
          <div className="mt-3 whitespace-pre-wrap text-slate-800">{ticket.user_response}</div>
        </section>
      )}

      {!showResolution && terminal && (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-slate-600">No resolution message is available for this ticket.</p>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Your request
        </h2>
        <p className="mt-3 whitespace-pre-wrap text-slate-800">{ticket.description}</p>
      </section>

      <details className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <summary className="cursor-pointer text-sm font-semibold text-slate-700">Details</summary>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Diagnosis</dt>
            <dd className="mt-1 text-slate-800">{ticket.diagnosis ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Resolution plan</dt>
            <dd className="mt-1 whitespace-pre-wrap text-slate-800">{ticket.resolution ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Confidence</dt>
            <dd className="mt-1 text-slate-800">
              {ticket.confidence != null ? `${Math.round(ticket.confidence * 100)}%` : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Escalated</dt>
            <dd className="mt-1 text-slate-800">{ticket.escalated ? "Yes" : "No"}</dd>
          </div>
          {latestRun && (
            <>
              <div>
                <dt className="text-slate-500">Latest run</dt>
                <dd className="mt-1 font-mono text-xs text-slate-800">{latestRun.id}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Run completed</dt>
                <dd className="mt-1 text-slate-800">{formatDate(latestRun.completed_at)}</dd>
              </div>
            </>
          )}
        </dl>
      </details>
    </div>
  );
}
