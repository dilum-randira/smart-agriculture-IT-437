import { useEffect, useState } from "react";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";

const sections = [
  {
    path: "/monitoring",
    name: "Field Monitoring",
    shortName: "Monitoring",
    description: "Follow field conditions and understand the quality of collected observations.",
    planned: ["Sensor readings and their timestamps", "Data-quality and missing-reading indicators", "Field history and trends"],
  },
  {
    path: "/predictions",
    name: "Predictions",
    shortName: "Predictions",
    description: "Explore forecast conditions and future fresh Nai Miris yield estimates.",
    planned: ["Microclimate forecast charts", "Prediction uncertainty and data freshness", "Fresh yield estimates when reliable labels are available"],
  },
  {
    path: "/irrigation",
    name: "Irrigation Planning",
    shortName: "Irrigation",
    description: "Compare irrigation planning options based on field data and future conditions.",
    planned: ["Water requirements and field stress", "Irrigation schedule options", "Water use and risk trade-offs"],
  },
  {
    path: "/harvest",
    name: "Harvest & Market",
    shortName: "Harvest & Market",
    description: "Review harvest timing and market scenarios with clearly explained assumptions.",
    planned: ["Market-price history and forecasts", "Harvest-date comparisons", "Explanations and scenario limitations"],
  },
];

const navigation = [{ path: "/", shortName: "Overview" }, ...sections];
const apiBase = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-3 rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-700" aria-label="Nai Miris, go to Overview">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-800 text-lg font-bold text-white" aria-hidden="true">N</span>
          <span className="leading-tight">
            <span className="block text-base font-bold tracking-tight text-slate-900">Nai Miris</span>
            <span className="block text-xs text-slate-500">Smart Agriculture</span>
          </span>
        </Link>
        <nav aria-label="Main navigation" className="flex w-full items-center gap-1 overflow-x-auto pb-1 sm:w-auto sm:pb-0">
          {navigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                "shrink-0 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700" +
                (isActive
                  ? " bg-emerald-50 text-emerald-900"
                  : " text-slate-600 hover:bg-slate-100 hover:text-slate-900")
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

function ApiConnection() {
  const [status, setStatus] = useState("checking");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    async function check() {
      try {
        const response = await fetch(apiBase + "/health", { signal: controller.signal });
        if (!response.ok) throw new Error("API returned an error");
        const data = await response.json();
        if (data.status !== "ok" || data.service !== "shared-backend") {
          throw new Error("Unexpected health response");
        }
        if (active) setStatus("connected");
      } catch (error) {
        if (active && error.name !== "AbortError") setStatus("unavailable");
      }
    }
    check();
    return () => {
      active = false;
      controller.abort();
    };
  }, [attempt]);

  const isConnected = status === "connected";
  return (
    <section aria-label="Backend connection" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Development connection</p>
      <div className="mt-4 flex items-center gap-2" aria-live="polite">
        <span className={"h-2.5 w-2.5 rounded-full " + (isConnected ? "bg-emerald-600" : status === "checking" ? "bg-amber-500" : "bg-slate-400")} aria-hidden="true" />
        <span className="font-semibold text-slate-900">
          {isConnected ? "Backend connected" : status === "checking" ? "Checking backend…" : "Backend not connected"}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        {isConnected
          ? "The shared FastAPI health endpoint is responding. Individual research APIs are not connected yet."
          : "Start the FastAPI server locally to check the connection. This does not indicate any live field data."}
      </p>
      <button
        type="button"
        onClick={() => { setStatus("checking"); setAttempt((value) => value + 1); }}
        className="mt-4 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
      >
        Check again
      </button>
    </section>
  );
}

function Overview() {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_330px]">
        <section className="rounded-2xl border border-emerald-100 bg-emerald-50 p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-widest text-emerald-800">Open-field research platform</p>
          <h1 className="mt-4 max-w-2xl text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Better field decisions start with trustworthy data.
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-700 sm:text-base">
            A shared workspace for monitoring, forecasting, irrigation planning and harvest decisions
            for Nai Miris cultivation. Each research area will be integrated as the team develops it.
          </p>
          <p className="mt-5 text-xs font-medium text-emerald-900">Research prototype · Component integration in progress</p>
        </section>
        <ApiConnection />
      </div>

      <section className="mt-12" aria-labelledby="areas-heading">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-emerald-800">Explore the platform</p>
            <h2 id="areas-heading" className="mt-2 text-2xl font-bold tracking-tight text-slate-900">Research areas</h2>
          </div>
          <p className="text-sm text-slate-500">Modules will be added by their owners.</p>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {sections.map((section, index) => (
            <Link
              key={section.path}
              to={section.path}
              className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-colors hover:border-emerald-300 hover:bg-emerald-50/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
            >
              <span className="text-xs font-semibold text-emerald-800">0{index + 1} / Research area</span>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">{section.name}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{section.description}</p>
              <span className="mt-5 inline-flex items-center text-sm font-semibold text-emerald-800">
                Open workspace <span className="ml-2 transition-transform group-hover:translate-x-1" aria-hidden="true">→</span>
              </span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}

function ModuleWorkspace({ section }) {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
      <Link to="/" className="text-sm font-medium text-emerald-800 hover:underline">← Back to overview</Link>
      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 sm:p-9">
        <p className="text-xs font-semibold uppercase tracking-widest text-emerald-800">Research workspace</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">{section.name}</h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">{section.description}</p>
        <div className="mt-8 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="font-semibold text-amber-950">Component integration pending</p>
          <p className="mt-1 text-sm leading-6 text-amber-900">
            This navigation route works, but this component’s real pages, data and APIs
            will be implemented by its research member. No sample results are presented as real data.
          </p>
        </div>
        <h2 className="mt-9 text-lg font-semibold text-slate-900">Planned workspace content</h2>
        <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-700">
          {section.planned.map((item) => (
            <li key={item} className="flex gap-3">
              <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-emerald-600" aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

function NotFound() {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-16 sm:px-6">
      <h1 className="text-3xl font-bold text-slate-900">Page not found</h1>
      <p className="mt-3 text-slate-600">That address is not part of the shared dashboard.</p>
      <Link to="/" className="mt-6 inline-block font-semibold text-emerald-800 hover:underline">Return to overview →</Link>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
        <Header />
        <Routes>
          <Route path="/" element={<Overview />} />
          {sections.map((section) => (
            <Route key={section.path} path={section.path} element={<ModuleWorkspace section={section} />} />
          ))}
          <Route path="*" element={<NotFound />} />
        </Routes>
        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-2 px-4 py-5 text-xs text-slate-500 sm:px-6">
            <span>Nai Miris Smart Agriculture</span>
            <span>Research prototype · No live farm results shown</span>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}
