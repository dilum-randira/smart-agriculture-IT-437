const areas = [
  { key: "C1", label: "IoT Monitoring" },
  { key: "C2", label: "Predictive Intelligence" },
  { key: "C3", label: "Irrigation Optimisation" },
  { key: "C4", label: "Harvest Decision Support" },
] as const;

export default function App() {
  return (
    <main className="min-h-screen bg-slate-50 px-5 py-12 text-slate-900 sm:px-8">
      <div className="mx-auto max-w-4xl">
        <p className="mb-3 text-sm font-semibold tracking-wide text-emerald-800">
          Smart Agriculture Research
        </p>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Nai Miris Research Dashboard
        </h1>
        <p className="mt-4 max-w-2xl text-slate-600">
          Shared React + Vite foundation. Individual component pages will be
          created by the respective research members.
        </p>
        <section aria-label="Planned research sections" className="mt-10 grid gap-4 sm:grid-cols-2">
          {areas.map((area) => (
            <div className="rounded-xl border border-slate-200 bg-white p-5" key={area.key}>
              <span className="text-xs font-semibold text-emerald-800">{area.key}</span>
              <h2 className="mt-2 text-lg font-semibold">{area.label}</h2>
              <p className="mt-2 text-sm text-slate-500">Page not implemented yet.</p>
            </div>
          ))}
        </section>
        <p className="mt-8 text-sm text-slate-500">
          No live sensor data, trained prediction, irrigation schedule, or
          harvest recommendation is displayed in this scaffold.
        </p>
      </div>
    </main>
  );
}
