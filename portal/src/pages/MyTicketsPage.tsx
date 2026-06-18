import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listMyTickets } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useUser } from "../context/UserContext";
import { formatDate, isTerminal } from "../lib/status";

export function MyTicketsPage() {
  const { userId } = useUser();

  const { data, isLoading, error, refetch, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ["tickets", userId],
    queryFn: () => listMyTickets(userId!),
    enabled: Boolean(userId),
    refetchInterval: (query) => {
      const tickets = query.state.data ?? [];
      const hasActive = tickets.some((t) => !isTerminal(t.status));
      return hasActive ? 12_000 : false;
    },
  });

  const tickets = data ?? [];

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">My tickets</h1>
          <p className="mt-1 text-sm text-slate-500">
            {dataUpdatedAt
              ? `Last updated ${new Date(dataUpdatedAt).toLocaleTimeString()}`
              : "Your submitted requests"}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {isFetching ? "Refreshing…" : "Refresh"}
          </button>
          <Link
            to="/"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            New ticket
          </Link>
        </div>
      </div>

      {isLoading && <p className="mt-8 text-slate-500">Loading tickets…</p>}

      {error && (
        <div className="mt-8 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Could not load tickets. Is the API running on port 8000?
        </div>
      )}

      {!isLoading && !error && tickets.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <p className="text-slate-600">No tickets yet.</p>
          <Link to="/" className="mt-4 inline-block text-sm font-medium text-blue-600 hover:underline">
            Submit your first request
          </Link>
        </div>
      )}

      {tickets.length > 0 && (
        <div className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">ID</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Subject</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Updated</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {tickets.map((ticket) => (
                <tr key={ticket.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs text-slate-700">{ticket.id}</td>
                  <td className="px-4 py-3 font-medium text-slate-900">{ticket.title}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={ticket.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-600">{formatDate(ticket.updated_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/tickets/${ticket.id}`}
                      className="font-medium text-blue-600 hover:underline"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
