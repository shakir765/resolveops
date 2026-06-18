import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createTicket, processTicket } from "../api/client";
import { useUser } from "../context/UserContext";

export function NewTicketPage() {
  const { userId } = useUser();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [successId, setSuccessId] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!userId) return;
    setError(null);
    setSubmitting(true);
    try {
      const ticket = await createTicket({ title, description, user_id: userId });
      await processTicket(ticket.id);
      setSuccessId(ticket.id);
      setTitle("");
      setDescription("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit ticket");
    } finally {
      setSubmitting(false);
    }
  }

  if (successId) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-8">
        <h1 className="text-xl font-semibold text-emerald-900">Ticket submitted</h1>
        <p className="mt-2 text-sm text-emerald-800">
          Reference: <span className="font-mono font-medium">{successId}</span>
        </p>
        <p className="mt-1 text-sm text-emerald-800">
          Your request is queued for automated processing. This page will update when the run
          completes.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to={`/tickets/${successId}`}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            View ticket
          </Link>
          <button
            type="button"
            onClick={() => setSuccessId(null)}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Submit another
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-900">Submit a request</h1>
      <p className="mt-2 text-slate-600">Describe your issue and we will investigate.</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="title" className="block text-sm font-medium text-slate-700">
            Subject *
          </label>
          <input
            id="title"
            required
            minLength={3}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Cannot connect to VPN"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-slate-700">
            Description *
          </label>
          <textarea
            id="description"
            required
            minLength={10}
            rows={6}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Error 619 when connecting from home office..."
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
        </div>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate("/tickets")}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {submitting ? "Submitting…" : "Submit ticket"}
          </button>
        </div>
      </form>
    </div>
  );
}
