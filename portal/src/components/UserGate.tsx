import { type FormEvent, useState } from "react";
import { useUser } from "../context/UserContext";

export function UserGate({ children }: { children: React.ReactNode }) {
  const { userId, setUserId } = useUser();
  const [input, setInput] = useState("");

  if (userId) return <>{children}</>;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setUserId(input);
  }

  return (
    <div className="mx-auto max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
      <h1 className="text-xl font-semibold text-slate-900">Welcome</h1>
      <p className="mt-2 text-sm text-slate-600">
        Enter your work user ID or email to view and submit IT tickets.
      </p>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="userId" className="block text-sm font-medium text-slate-700">
            User ID
          </label>
          <input
            id="userId"
            type="text"
            required
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="jsmith"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
        </div>
        <button
          type="submit"
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          Continue
        </button>
      </form>
    </div>
  );
}
