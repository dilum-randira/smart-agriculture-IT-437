import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

/**
 * Shared navigation only. Component-specific pages are owned by the team.
 * Desktop: horizontal links. Mobile: compact accessible menu.
 */
export default function Navbar({ navigation }) {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link
          to="/"
          onClick={() => setIsOpen(false)}
          className="flex items-center gap-3 rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-700"
          aria-label="Nai Miris, go to Overview"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-800 text-lg font-bold text-white" aria-hidden="true">
            N
          </span>
          <span className="leading-tight">
            <span className="block text-base font-bold tracking-tight text-slate-900">Nai Miris</span>
            <span className="block text-xs text-slate-500">Smart Agriculture</span>
          </span>
        </Link>

        <button
          type="button"
          aria-controls="primary-navigation"
          aria-expanded={isOpen}
          aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
          onClick={() => setIsOpen((value) => !value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 sm:hidden"
        >
          {isOpen ? "Close" : "Menu"}
        </button>

        <nav
          id="primary-navigation"
          aria-label="Main navigation"
          className={
            "w-full flex-col gap-1 rounded-xl border border-slate-100 bg-white p-2 sm:flex sm:w-auto sm:flex-row sm:items-center sm:border-0 sm:p-0 " +
            (isOpen ? "flex" : "hidden")
          }
        >
          {navigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              onClick={() => setIsOpen(false)}
              className={({ isActive }) =>
                "rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 " +
                (isActive
                  ? "bg-emerald-50 text-emerald-900"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900")
              }
            >
              {item.shortName}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
