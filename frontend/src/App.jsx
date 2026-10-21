import { lazy, Suspense } from "react";
import { BrowserRouter, Link, Outlet, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import YieldPrediction from "./pages/c2/YieldPrediction";
import AuthProvider, { useAuth } from "./auth/AuthProvider";
import RequireAuth from "./auth/RequireAuth";
import { navigationForRole } from "./services/navigation";
import Login from "./pages/Login";
import Register from "./pages/Register";
import FarmWorkspace from "./pages/c2/FarmWorkspace";
import AccessDenied from "./pages/AccessDenied";
import "./styles/auth.css";
const MicroclimateForecasting = lazy(() => import("./pages/c2/MicroclimateForecasting"));
const FarmManagement = lazy(() => import("./pages/c2/FarmManagement"));

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
    path: "/integration",
    name: "Integration",
    shortName: "Integration",
    description: "Review component integration status. Device and farm data integrations are not implemented here.",
    planned: ["Verified component interfaces", "Device ingestion and calibration contracts"],
  },
  {
    path: "/harvest",
    name: "Harvest & Market",
    shortName: "Harvest & Market",
    description: "Review harvest timing and market scenarios with clearly explained assumptions.",
    planned: ["Market-price history and forecasts", "Harvest-date comparisons", "Explanations and scenario limitations"],
  },
];


function Overview() { return <FarmWorkspace view="overview" />; }

function ModuleWorkspace({ section }) {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
      <Link to="/" className="text-sm font-medium text-emerald-800 hover:underline">← Back to overview</Link>
      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 sm:p-9">
        <p className="text-xs font-semibold uppercase tracking-widest text-emerald-800">Smart Agriculture</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">{section.name}</h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">{section.description}</p>
        <p className="mt-3 text-sm text-slate-600">Read-only placeholder. No private farm data or farm-level ownership mapping is implemented in this section.</p>
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

function AppLayout() {
  const { user } = useAuth();
  const items = navigationForRole(user.role);
  return (
      <div className="application-shell">
        <Navbar navigation={items} />
        <div className="application-body"><Outlet />
        <footer className="border-t border-slate-200 bg-white"><div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-2 px-4 py-5 text-xs text-slate-500 sm:px-6"><span>Nai Miris Smart Agriculture</span><span>Sample data is clearly identified · No live sensor connection</span></div></footer></div>
      </div>
  );
}

export default function App() {
  return <BrowserRouter><AuthProvider><Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/register" element={<Register />} />
    <Route element={<RequireAuth />}><Route element={<AppLayout />}>
          <Route path="/access-denied" element={<AccessDenied />} />
          <Route path="/farms" element={<FarmWorkspace view="farms" />} />
          <Route path="/sensors" element={<FarmWorkspace view="sensors" />} />
          <Route path="/monitoring" element={<FarmWorkspace view="monitoring" />} />
          <Route path="/account" element={<FarmWorkspace view="account" />} />
          <Route path="/predictions/manage" element={<Suspense fallback={<main role="status">Loading local administration…</main>}><FarmManagement /></Suspense>} />
          <Route path="/predictions/microclimate" element={<Suspense fallback={<main className="mx-auto w-full max-w-6xl flex-1 px-6 py-16" role="status">Loading Microclimate workspace…</main>}><MicroclimateForecasting /></Suspense>} />
          <Route path="/" element={<Overview />} />
          <Route path="/predictions/yield" element={<YieldPrediction />} />
          {sections.filter((section) => section.path !== "/monitoring").map((section) => (
            <Route key={section.path} path={section.path} element={section.path === "/predictions" ? <YieldPrediction /> : <ModuleWorkspace section={section} />} />
          ))}
          <Route path="*" element={<NotFound />} />
    </Route></Route>
  </Routes></AuthProvider></BrowserRouter>;
}
