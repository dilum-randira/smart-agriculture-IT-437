// C3 Irrigation Operations Dashboard.
// Live demo: today's REAL forecast at the demo location -> NSGA-II plan, the
// facts behind each day, and what reactive rules would do instead.
// Synthetic mode: the synthetic sample files. Soil and crop values are
// placeholders / proxies in both modes until field data exists.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const DEFICIT_CHOICES = [0, 0.05, 0.1];

function useJson(url) {
  const [state, setState] = useState({ status: "loading", data: null, error: null });
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading", data: null, error: null });
    fetch(url, { signal: controller.signal })
      .then(async (response) => {
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || `API returned ${response.status}`);
        setState({ status: "ready", data: body, error: null });
      })
      .catch((error) => {
        if (error.name !== "AbortError") setState({ status: "error", data: null, error: error.message });
      });
    return () => controller.abort();
  }, [url]);
  return state;
}

function Card({ title, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-500">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Message({ state, what }) {
  if (state.status === "loading") return <p className="text-sm text-slate-500">Loading {what}…</p>;
  return <p className="text-sm text-amber-900">Could not load {what}: {state.error}</p>;
}

function Notice({ title, children }) {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
      <p className="font-semibold text-amber-950">{title}</p>
      <p className="mt-1 text-sm leading-6 text-amber-900">{children}</p>
    </div>
  );
}

function Table({ columns, rows, highlight }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs uppercase text-slate-500">
          <tr>{columns.map((c) => <th key={c.label} className="py-2 pr-4">{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className={"border-t border-slate-100 " + (highlight && highlight(row) ? "bg-emerald-50 font-semibold" : "")}>
              {columns.map((c) => <td key={c.label} className="py-2 pr-4 align-top">{c.value(row)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SoilBar({ soil }) {
  const percent = (value) => `${Math.min(100, (value / soil.taw_mm) * 100)}%`;
  return (
    <div>
      <div className="relative h-3 rounded-full bg-slate-100" aria-hidden="true">
        <div className="h-3 rounded-full bg-sky-600" style={{ width: percent(soil.depletion_mm) }} />
        <div className="absolute top-[-4px] h-5 w-0.5 bg-amber-600" style={{ left: percent(soil.raw_mm) }} />
      </div>
      <p className="mt-2 text-xs text-slate-600">
        Root zone {soil.depletion_mm} mm dry · stress starts at {soil.raw_mm} mm (amber line) · empty at {soil.taw_mm} mm
      </p>
    </div>
  );
}

function TodayCard({ plan }) {
  const { today, soil } = plan;
  return (
    <Card title={`Today · ${today.date}`}>
      <p className={"text-2xl font-bold " + (today.irrigate ? "text-sky-800" : "text-slate-900")}>
        {today.irrigate ? `Irrigate ${today.amount_mm} mm` : "No irrigation today"}
      </p>
      {today.irrigate && <p className="mt-1 text-sm text-slate-600">{today.volume_m3} m³ for the plot</p>}
      {!plan.meets_allowed_deficit && (
        <p className="mt-2 text-sm text-amber-900">No plan meets the allowed shortfall; showing the least-stress plan.</p>
      )}
      <div className="mt-5"><SoilBar soil={soil} /></div>
    </Card>
  );
}

function WeekPlan({ plan }) {
  return (
    <Card title="7-day plan">
      <ol className="grid grid-cols-7 gap-2">
        {plan.plan.map((day, i) => (
          <li key={day.date} className={"rounded-lg border p-2 text-center text-xs " +
            (day.irrigate ? "border-sky-300 bg-sky-50 text-sky-900" : "border-slate-200 text-slate-600")}>
            <span className="block font-semibold">{day.date.slice(5)}</span>
            <span className="mt-1 block">{day.irrigate ? `${day.amount_mm} mm` : "—"}</span>
            {plan.days && <span className="mt-1 block text-[11px] text-slate-500">{plan.days[i].rain_forecast_mm} mm rain</span>}
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-slate-500">Recalculated every day with the newest soil reading and forecast.</p>
    </Card>
  );
}

function WhyTable({ plan }) {
  return (
    <Card title="Why this plan (if the forecast comes true)">
      <Table rows={plan.days} columns={[
        { label: "Date", value: (r) => r.date },
        { label: "Rain forecast", value: (r) => `${r.rain_forecast_mm} mm` },
        { label: "ET₀", value: (r) => `${r.et0_mm_day} mm` },
        { label: "Root zone dry", value: (r) => `${r.depletion_morning_mm} mm` },
        { label: "Decision", value: (r) => r.reason },
      ]} />
    </Card>
  );
}

function PredictiveVsReactive({ plan }) {
  return (
    <Card title="Predictive vs reactive this week">
      <Table rows={plan.week_comparison} highlight={(r) => r.schedule.startsWith("C3 (uses")} columns={[
        { label: "Schedule", value: (r) => r.schedule },
        { label: "Water", value: (r) => `${r.water_mm} mm` },
        { label: "Irrigations", value: (r) => r.irrigations },
        { label: "Crop water shortfall", value: (r) => `${(r.relative_et_deficit * 100).toFixed(1)} %` },
        { label: "Water lost to drainage", value: (r) => `${r.drainage_mm} mm` },
      ]} />
      <p className="mt-3 text-xs text-slate-500">
        Same soil, same 7 days, assuming the forecast comes true. "Ignoring forecast rain" plans as if no rain falls;
        the fixed threshold reacts to the soil only.
      </p>
    </Card>
  );
}

function OptionsTable({ plan }) {
  const chosen = plan.chosen_objectives;
  const isChosen = (row) => Object.keys(chosen).every((key) => Math.abs(row[key] - chosen[key]) < 1e-9);
  const days = [1, 2, 3, 4, 5, 6, 7].filter((d) => `day${d}_irrigate` in plan.pareto_front[0]);
  return (
    <Card title="Trade-off options (NSGA-II Pareto front)">
      <Table rows={plan.pareto_front} highlight={isChosen} columns={[
        { label: "Water (mm)", value: (r) => r.total_water_mm.toFixed(1) },
        { label: "Crop water shortfall", value: (r) => `${(r.relative_et_deficit * 100).toFixed(1)} %` },
        { label: "Irrigations", value: (r) => r.irrigation_events },
        { label: "Root-rot risk days", value: (r) => r.root_rot_risk_days },
        { label: "Days (● irrigate)", value: (r) => <span className="font-mono text-xs">{days.map((d) => (r[`day${d}_irrigate`] ? "●" : "·")).join(" ")}</span> },
      ]} />
      <p className="mt-3 text-xs text-slate-500">Highlighted = chosen plan (least water within the allowed shortfall).</p>
    </Card>
  );
}

function SeasonTable({ url, title, highlight }) {
  const state = useJson(url);
  return (
    <Card title={title}>
      {state.status !== "ready" ? <Message state={state} what="the season comparison" /> : (
        <>
          <p className="mb-3 text-xs text-slate-500">{state.data.note}</p>
          <Table rows={state.data.rows} highlight={highlight} columns={[
            { label: "Schedule", value: (r) => r.schedule },
            { label: "Water (mm)", value: (r) => r.total_irrigation_mm.toFixed(0) },
            { label: "Irrigations", value: (r) => r.irrigation_events },
            { label: "Stress days", value: (r) => r.stress_days },
            { label: "Drainage (mm)", value: (r) => r.total_deep_percolation_mm.toFixed(1) },
            { label: "Root-rot risk days", value: (r) => r.root_rot_risk_days },
          ]} />
        </>
      )}
    </Card>
  );
}

function Controls({ mode, issueDate, setIssueDate, soilMoisture, setSoilMoisture, deficit, setDeficit }) {
  const input = "mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2";
  return (
    <form className="mt-6 grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-3" onSubmit={(e) => e.preventDefault()}>
      {mode === "synthetic" ? (
        <label className="text-sm font-medium text-slate-700">Forecast issued on
          <input type="date" value={issueDate} min="2024-01-01" max="2025-12-23"
            onChange={(e) => setIssueDate(e.target.value)} className={input} />
        </label>
      ) : (
        <div className="text-sm font-medium text-slate-700">Forecast
          <p className="mt-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-normal text-slate-600">Live, issued today</p>
        </div>
      )}
      <label className="text-sm font-medium text-slate-700">Soil moisture now (m³/m³)
        <input type="number" step="0.01" min="0" max="0.5" value={soilMoisture}
          onChange={(e) => setSoilMoisture(e.target.value)} className={input} />
      </label>
      <label className="text-sm font-medium text-slate-700">Allowed crop water shortfall
        <select value={deficit} onChange={(e) => setDeficit(e.target.value)} className={input}>
          {DEFICIT_CHOICES.map((value) => <option key={value} value={value}>{value * 100} %</option>)}
        </select>
      </label>
    </form>
  );
}

export default function IrrigationPlanning({ apiBase }) {
  const [mode, setMode] = useState("live");
  const [issueDate, setIssueDate] = useState("2025-06-01");
  const [soilMoisture, setSoilMoisture] = useState(0.17);
  const [deficit, setDeficit] = useState(0);

  const query = new URLSearchParams({ soil_moisture_m3m3: soilMoisture, max_relative_et_deficit: deficit });
  if (mode === "synthetic") query.set("issue_date", issueDate);
  const plan = useJson(`${apiBase}/c3/demo/${mode === "live" ? "live-plan" : "plan"}?${query}`);
  const tab = (value, label) => (
    <button type="button" onClick={() => setMode(value)} aria-pressed={mode === value}
      className={"rounded-lg px-4 py-2 text-sm font-semibold " + (mode === value ? "bg-emerald-700 text-white" : "border border-slate-300 text-slate-700 hover:bg-slate-50")}>
      {label}
    </button>
  );

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
      <Link to="/" className="text-sm font-medium text-emerald-800 hover:underline">← Back to overview</Link>
      <h1 className="mt-6 text-3xl font-bold tracking-tight text-slate-900">Irrigation Planning</h1>
      <p className="mt-2 max-w-2xl text-slate-600">C3 · Adaptive multi-objective irrigation optimisation (FAO-56 water balance + NSGA-II).</p>

      <div className="mt-6 flex flex-wrap gap-2">{tab("live", "Live demo (real forecast)")}{tab("synthetic", "Synthetic data")}</div>

      <div className="mt-4">
        {mode === "live" ? (
          <Notice title="Live demo · Mahailuppallama (demo location, not the test plot)">
            Uses today's real weather forecast (Open-Meteo). Soil values are placeholders and crop values are the FAO-56
            bell pepper proxy until field data is available.
          </Notice>
        ) : (
          <Notice title="Synthetic demonstration">
            Weather, forecasts, soil and crop values are synthetic, placeholders or proxies. Nothing here is a research result.
          </Notice>
        )}
      </div>

      <Controls {...{ mode, issueDate, setIssueDate, soilMoisture, setSoilMoisture, deficit, setDeficit }} />

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {plan.status === "ready" ? (<><TodayCard plan={plan.data} /><WeekPlan plan={plan.data} /></>)
          : <Card title="Today"><Message state={plan} what="the plan" /></Card>}
      </div>
      {plan.status === "ready" && (
        <div className="mt-6 space-y-6">
          <WhyTable plan={plan.data} />
          <PredictiveVsReactive plan={plan.data} />
          <OptionsTable plan={plan.data} />
        </div>
      )}
      <div className="mt-6">
        {mode === "live"
          ? <SeasonTable url={`${apiBase}/c3/demo/evaluation-real`} title="Past season on real weather and real forecasts (Yala 2025)"
              highlight={(r) => r.schedule.startsWith("NSGA-II")} />
          : <SeasonTable url={`${apiBase}/c3/demo/evaluation`} title="Season comparison with baselines (synthetic)" />}
      </div>
    </main>
  );
}
