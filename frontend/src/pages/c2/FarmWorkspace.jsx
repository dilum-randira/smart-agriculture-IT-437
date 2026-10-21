import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Asset, { AssetIcon } from "../../components/ui/Asset";
import { avatarAsset } from "../../services/uiAssets";
import { useAuth } from "../../auth/AuthProvider";
import { ROLE_LABELS } from "../../auth/policy";
import { accessApi, selectionQuery } from "../../services/c2/accessApi";
import { farmSummary } from "../../services/c2/farmSummary";
import { LocationPlot } from "../../components/c2/microclimate/FarmAccess";
import "../../styles/c2/access.css";
import "../../styles/c2/farms.css";

function RecentForecasts({ farms }) {
  const [state, setState] = useState({ loading: true, items: [], error: "" });
  useEffect(() => {
    const controller = new AbortController();
    const selections = farms.flatMap((farm) => farm.sites.flatMap((site) => site.nodes.map((node) => ({ farm, site, node })))).slice(0, 8);
    setState({ loading: true, items: [], error: "" });
    Promise.all(selections.map(async ({ farm, site, node }) => {
      const data = await accessApi(`/farms/${farm.farm_id}/forecasts?${selectionQuery(site.site_id, node.node_id)}`, { signal: controller.signal });
      return data.map((item) => ({ id: item.forecast_id, model: item.model, created: item.created, node: node.node_id, sample: farm.is_demo }));
    })).then((groups) => { if (!controller.signal.aborted) setState({ loading: false, items: groups.flat().sort((a, b) => b.created - a.created).slice(0, 6), error: "" }); })
      .catch((failure) => { if (!controller.signal.aborted) setState({ loading: false, items: [], error: failure.message }); });
    return () => controller.abort();
  }, [farms]);
  return <section className="farm-card"><h2>Recent saved forecasts</h2>{state.loading ? <p role="status">Loading forecast history…</p> : state.error ? <p role="alert">{state.error}</p> : state.items.length ? <ul className="farm-recent">{state.items.map((item) => <li key={item.id}><strong>{item.node} · {item.model.replaceAll("_", " ")}</strong><span>{new Date(item.created * 1000).toLocaleString()} {item.sample ? "· Sample Data" : ""}</span></li>)}</ul> : <div className="ui-empty"><Asset name="noForecast" width={115} height={80} /><p>No saved forecasts available for your assigned nodes yet.</p></div>}<p>Latest records from up to eight assigned nodes. Open Forecast Insights for full saved outputs.</p><Link to="/predictions/microclimate">Open forecast history →</Link></section>;
}

function FarmForm({ farm, onSave, busy }) {
  return <form className="farm-form" onSubmit={onSave}><fieldset disabled={busy}><legend>{farm ? "Edit your farm" : "Add a farm"}</legend><label>Farm name<input name="farm_name" defaultValue={farm?.farm_name || ""} minLength={2} maxLength={100} required /></label><label>District<input name="district" defaultValue={farm?.district || ""} minLength={2} maxLength={80} required /></label><label>Crop type<input name="crop_type" defaultValue={farm?.crop_type || "Capsicum chinense"} minLength={2} maxLength={80} required /></label><label>Latitude (optional)<input name="latitude" type="number" step="any" min="-90" max="90" defaultValue={farm?.latitude ?? ""} /></label><label>Longitude (optional)<input name="longitude" type="number" step="any" min="-180" max="180" defaultValue={farm?.longitude ?? ""} /></label><label>Timezone<input name="timezone" defaultValue={farm?.timezone || "Asia/Colombo"} required maxLength={64} /></label><button type="submit">{busy ? "Saving…" : farm ? "Save farm details" : "Create my farm"}</button></fieldset><p>Supply both coordinates or leave both blank. Location is unverified metadata and does not adjust model predictions. Sensor assignment is managed by an administrator.</p></form>;
}

export default function FarmWorkspace({ view = "overview" }) {
  const { user } = useAuth();
  const [farms, setFarms] = useState([]), [loading, setLoading] = useState(true);
  const [error, setError] = useState(""), [status, setStatus] = useState(""), [busy, setBusy] = useState(false), [editing, setEditing] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    accessApi("/farms", { signal: controller.signal }).then((data) => { if (!controller.signal.aborted) setFarms(data.filter((farm) => farm.assigned)); })
      .catch((failure) => { if (!controller.signal.aborted) setError(failure.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [user.id, retry]);
  async function save(event, farm) {
    event.preventDefault(); const form = event.currentTarget, data = new FormData(form);
    const coordinate = (name) => data.get(name) === "" ? null : Number(data.get(name));
    const body = { farm_name: data.get("farm_name"), district: data.get("district"), crop_type: data.get("crop_type"), latitude: coordinate("latitude"), longitude: coordinate("longitude"), timezone: data.get("timezone"), growth_stage: farm?.growth_stage || null };
    setBusy(true); setError(""); setStatus("");
    try {
      await accessApi(farm ? `/farms/${farm.farm_id}` : "/farms", { method: farm ? "PUT" : "POST", body });
      setStatus(farm ? "Farm details saved." : "Farm created and assigned to your account. Sensor data is unavailable until verified observations are connected.");
      form.reset(); setEditing(""); setRetry((value) => value + 1);
    } catch (failure) { setError(failure.status === 422 ? "Check all fields, coordinate ranges, coordinate pairs and timezone." : failure.message); }
    finally { setBusy(false); }
  }
  const summary = farmSummary(farms);
  const title = { overview: `Welcome, ${user.username}.`, farms: "My Farms", sensors: "Sensor Nodes", monitoring: "Environmental Monitoring", account: "Your Account" }[view];
  return <main className="farm-workspace"><header className="farm-heading"><div><span className="ui-page-icon"><AssetIcon name={{ overview: "overview", farms: "farms", sensors: "sensors", monitoring: "monitoring", account: "account" }[view]} size={26} /></span><p className="auth-eyebrow">Smart Agriculture</p><h1>{title}</h1><p>{view === "overview" ? "Your farms, available observations and forecast insights in one place." : "Only farms assigned to your account are shown."}</p></div><Link to="/predictions/microclimate" className="farm-primary">Forecast insights →</Link></header>
    {view === "account" ? <section className="farm-card"><div className="farm-account-identity"><Asset name={avatarAsset(user.role)} width={72} height={72} /><h2>Account details</h2></div><dl><dt>Username</dt><dd>{user.username}</dd><dt>Role</dt><dd>{ROLE_LABELS[user.role]}</dd></dl><p>Contact an administrator for role or membership changes. Roles cannot be changed from this page.</p></section> : <>
      {error && <div className="auth-error" role="alert"><AssetIcon name="error" size={19} /> {error} <button type="button" onClick={() => setRetry((value) => value + 1)}>Retry</button></div>}{status && <p className="farm-success ui-feedback" role="status"><AssetIcon name="notification" size={19} />{status}</p>}
      {loading ? <p role="status" className="farm-card">Loading your farms and sensors…</p> : <>
        <section className="farm-stats" aria-label="Assigned farm summary">{[["Farms", summary.farms], ["Sites", summary.sites], ["Nodes", summary.nodes], ["Nodes with sample history", summary.sampleNodes]].map(([label, value], index) => <article key={label}><AssetIcon name={["farms", "location", "sensors", "sample"][index]} size={24} /><span>{label}</span><strong>{value}</strong></article>)}</section>
        {view === "overview" && <nav className="farm-shortcuts" aria-label="Farm tools"><Link to="/farms"><AssetIcon name="farms" size={19} />My Farms →</Link><Link to="/monitoring"><AssetIcon name="monitoring" size={19} />Environmental Monitoring →</Link><Link to="/predictions/microclimate"><AssetIcon name="microclimate" size={19} />Microclimate Forecasting →</Link><Link to="/predictions"><AssetIcon name="yield" size={19} />Yield Prediction →</Link><Link to="/sensors"><AssetIcon name="sensors" size={19} />Sensor Nodes →</Link></nav>}
        {!farms.length && <section className="farm-card ui-empty"><Asset name="noFarms" width={145} height={110} /><div><h2>Your farm journey starts here.</h2><p>No farms are assigned yet. Add a farm in My Farms, or ask an administrator to assign an existing farm. No sensor readings or predictions are invented.</p><Link to="/farms">Open My Farms →</Link></div></section>}
        <div className="farm-grid">{farms.map((farm) => <article className="farm-card" key={farm.farm_id}><div className="farm-card-heading"><h2>{farm.farm_name}</h2>{!!farm.is_demo && <span className="farm-sample"><AssetIcon name="sample" size={14} />Sample Data — Not Live Sensor Readings</span>}</div><p>{farm.district} · {farm.crop_type} · {farm.timezone}</p><p>{farm.is_demo ? "Synthetic observations available for assigned sample nodes. Location not verified." : "Sensor data unavailable — no verified historical observations are connected."}</p>
          {!farm.is_demo && <LocationPlot latitude={farm.latitude} longitude={farm.longitude} />}
          {!farm.sites.length && <div className="farm-empty ui-empty"><Asset name="noSensors" width={100} height={75} /><p>No sites or sensors assigned. Ask an administrator to register and assign your sensor nodes.</p></div>}
          {farm.sites.map((site) => <section className="farm-site" key={site.site_id}><h3>{site.site_name}</h3>{site.nodes.length ? <ul>{site.nodes.map((node) => <li key={node.node_id}><strong><AssetIcon name="sensors" size={18} />{node.node_id}</strong><span>{node.is_demo ? "Sample history available · Not a physical device" : "Sensor data unavailable"}</span>{view === "sensors" && <small>{node.sensor_metadata || "Sensor metadata unavailable"} · Calibration: {node.calibration_reference || "Not supplied"}</small>}</li>)}</ul> : <p>No registered nodes assigned to this site.</p>}</section>)}
          <Link to="/predictions/microclimate">Open farm forecasting →</Link>
          {view === "farms" && farm.owned && !farm.is_demo && <><button type="button" className="farm-edit" onClick={() => setEditing(editing === farm.farm_id ? "" : farm.farm_id)}>{editing === farm.farm_id ? "Cancel editing" : "Edit farm details"}</button>{editing === farm.farm_id && <FarmForm farm={farm} busy={busy} onSave={(event) => save(event, farm)} />}</>}
          {view === "farms" && !farm.owned && <p className="farm-empty">Assigned access. Farm metadata and sensor assignments are managed by the owner or an administrator.</p>}
        </article>)}</div>
      </>}
      {view === "farms" && ["viewer", "admin"].includes(user.role) && <section className="farm-card farm-create"><FarmForm busy={busy} onSave={(event) => save(event)} /></section>}
      {view === "overview" && !loading && <RecentForecasts farms={farms} />}
      <p className="farm-disclaimer">No live telemetry is connected. Sample forecasts do not establish real Nai Miris field accuracy. Coordinates select metadata only; the frozen models use historical environmental observations.</p>
    </>}
  </main>;
}
