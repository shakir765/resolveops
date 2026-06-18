import { Link, NavLink, Outlet } from "react-router-dom";
import { useUser } from "../context/UserContext";

export function Layout() {
  const { userId, clearUser } = useUser();

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-2 text-sm font-medium ${
      isActive ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"
    }`;

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Link to="/" className="text-lg font-semibold text-slate-900">
              ResolveOps Helpdesk
            </Link>
            {userId && (
              <p className="mt-0.5 text-sm text-slate-500">Signed in as {userId}</p>
            )}
          </div>
          <nav className="flex flex-wrap items-center gap-2">
            <NavLink to="/" end className={navClass}>
              New ticket
            </NavLink>
            <NavLink to="/tickets" className={navClass}>
              My tickets
            </NavLink>
            {userId && (
              <button
                type="button"
                onClick={clearUser}
                className="rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Switch user
              </button>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
