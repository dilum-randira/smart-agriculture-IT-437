import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AssetIcon } from "../../components/ui/Asset";
import { accessApi } from "../../services/c2/accessApi";
import { useAuth } from "../../auth/AuthProvider";
import "../../styles/c2/microclimate.css";
import "../../styles/c2/access.css";

export default function FarmManagement() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]), [farms, setFarms] = useState([]), [nodes, setNodes] = useState([]);
  const [farmId, setFarmId] = useState(""), [status, setStatus] = useState(""), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const farm = farms.find((item) => item.farm_id === farmId);
  async function refresh() { const [u, f, n] = await Promise.all([accessApi("/users"), accessApi("/farms"), accessApi("/nodes")]); setUsers(u); setFarms(f); setNodes(n); }
  useEffect(() => { if (user?.role === "admin") refresh().catch((err) => setError(err.message)); }, [user?.id, user?.role]);
  async function perform(event, operation) {
    event.preventDefault(); setError(""); setStatus(""); setBusy(true);
    const form = event.currentTarget, data = new FormData(form);
    try { await operation(data); await refresh(); setStatus("Saved. Backend permissions were checked."); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  if (user?.role !== "admin") return <main className="mc-dashboard mc-admin"><h1>Farm management</h1><p>Administrator access is required. Sign in through the forecasting workspace.</p>{error && <p role="alert">{error}</p>}<Link to="/predictions/microclimate">Return to Microclimate</Link></main>;
  return <main className="mc-dashboard mc-admin"><div className="mc-section-heading"><div><p className="mc-eyebrow">C2 · Local administration</p><h1><AssetIcon name="admin" size={30} />Users, farms & nodes</h1></div><Link to="/predictions/microclimate">← Forecast workspace</Link></div><p>Signed in as {user.username} · Admin. No real records or coordinates are pre-populated. Enter only information you are authorized to manage.</p>
    {error && <p className="mc-error" role="alert">{error}</p>}{status && <p role="status">{status}</p>}
    <fieldset disabled={busy} className="mc-admin-grid">
      <section className="mc-access"><h2>Create authorized user</h2><form onSubmit={(e) => perform(e, async (data) => { await accessApi("/users", { method: "POST", body: { username: data.get("username"), password: data.get("password"), role: data.get("role") } }); e.target.reset(); })}><label>Username<input name="username" minLength={3} maxLength={64} pattern="[a-zA-Z0-9_.-]+" required autoComplete="off" /></label><label>Initial password<input name="password" type="password" minLength={12} maxLength={128} required autoComplete="new-password" /></label><label>Role<select name="role"><option value="viewer">Farmer / Viewer</option><option value="researcher">Researcher</option><option value="admin">Admin</option></select></label><button>Create user</button></form><p>New users start without farm access. Assign membership below.</p></section>
      <section className="mc-access"><h2>Roles & account status</h2>{users.map((item) => <form key={item.id} className="mc-user-row" onSubmit={(e) => perform(e, (data) => accessApi(`/users/${item.id}`, { method: "PUT", body: { role: data.get("role"), active: data.get("active") === "on" } }))}><strong>{item.username}</strong><label>Role<select name="role" defaultValue={item.role}><option value="viewer">Farmer / Viewer</option><option value="researcher">Researcher</option><option value="admin">Admin</option></select></label><label className="mc-check"><input name="active" type="checkbox" defaultChecked={!!item.active} />Active</label><button>Save</button></form>)}<p>Role/status changes revoke that user's sessions. The last active administrator cannot be removed.</p></section>
    </fieldset>
    <section className="mc-access"><label>Manage farm<select value={farmId} onChange={(e) => setFarmId(e.target.value)}><option value="">Create a new farm record</option>{farms.map((item) => <option key={item.farm_id} value={item.farm_id}>{item.farm_name}{item.is_demo ? " (DEMO)" : ""}</option>)}</select></label>
      <form key={farmId} className="mc-admin-grid" onSubmit={(e) => perform(e, async (data) => {
        const coordinate = (value) => value === null || value === "" ? null : Number(value);
        const body = { farm_name: data.get("farm_name"), district: data.get("district"), latitude: coordinate(data.get("latitude")), longitude: coordinate(data.get("longitude")), timezone: data.get("timezone"), crop_type: data.get("crop_type"), growth_stage: data.get("growth_stage") || null };
        if (!farmId) body.is_demo = data.get("is_demo") === "on";
        const created = await accessApi(farmId ? `/farms/${farmId}` : "/farms", { method: farmId ? "PUT" : "POST", body }); setFarmId(created.farm_id);
      })}>
        <label>Farm name<input name="farm_name" required minLength={2} maxLength={100} defaultValue={farm?.farm_name || ""} /></label><label>District<input name="district" required minLength={2} maxLength={80} defaultValue={farm?.district || ""} /></label>
        <label>Latitude (optional; −90 to 90)<input name="latitude" type="number" step="any" min="-90" max="90" defaultValue={farm?.latitude ?? ""} disabled={!!farm?.is_demo} /></label><label>Longitude (optional; −180 to 180)<input name="longitude" type="number" step="any" min="-180" max="180" defaultValue={farm?.longitude ?? ""} disabled={!!farm?.is_demo} /></label>
        <label>IANA timezone<input name="timezone" required defaultValue={farm?.timezone || "Asia/Colombo"} maxLength={64} /></label><label>Crop type<input name="crop_type" required minLength={2} maxLength={80} defaultValue={farm?.crop_type || ""} /></label><label>Growth stage (optional, observed only)<input name="growth_stage" minLength={2} maxLength={80} defaultValue={farm?.growth_stage || ""} disabled={!!farm?.is_demo} /></label>
        {!farm && <label className="mc-check"><input name="is_demo" type="checkbox" />Explicitly synthetic demonstration record (coordinates/stage must be blank)</label>}<button disabled={busy}>Save farm metadata</button>
      </form><p>Coordinates and growth stage are metadata only. Supplied locations are not independently verified. No forecast inputs or output values are adjusted by GPS.</p>
    </section>
    {farm && <fieldset className="mc-admin-grid" disabled={busy}>
      <section className="mc-access"><h2>Farm membership</h2><p>Assigned users: {farm.members?.map((member) => `${member.username} (${member.role})`).join(", ") || "None"}</p><form onSubmit={(e) => perform(e, (data) => accessApi(`/farms/${farmId}/members/${data.get("user_id")}`, { method: "PUT", body: { granted: data.get("action") === "grant" } }))}><label>User<select name="user_id" required>{users.map((item) => <option key={item.id} value={item.id}>{item.username} · {item.role}</option>)}</select></label><label>Action<select name="action"><option value="grant">Grant farm access</option><option value="revoke">Revoke farm access</option></select></label><button>Apply membership</button></form><p>Membership and role are checked independently on every protected request.</p></section>
      <section className="mc-access"><h2>Sites</h2><form onSubmit={(e) => perform(e, (data) => accessApi(`/farms/${farmId}/sites`, { method: "POST", body: { site_name: data.get("site_name") } }))}><label>New site name<input name="site_name" minLength={2} maxLength={100} required /></label><button>Create site</button></form>{farm.sites.map((site) => <form key={site.site_id} onSubmit={(e) => perform(e, (data) => accessApi(`/farms/${farmId}/sites/${site.site_id}`, { method: "PUT", body: { site_name: data.get("site_name") } }))}><label>Rename site<input name="site_name" minLength={2} maxLength={100} required defaultValue={site.site_name} /></label><button>Save site name</button></form>)}<p>Sites inherit displayed farm-location context; no sensor GPS position is inferred.</p></section>
      <section className="mc-access"><h2>Assign registered node</h2><form onSubmit={(e) => perform(e, (data) => accessApi(`/farms/${farmId}/nodes/${data.get("node_id")}`, { method: "PUT", body: { site_id: data.get("site_id") } }))}><label>Node<select name="node_id" required>{nodes.map((item) => <option key={item.node_id}>{item.node_id}</option>)}</select></label><label>Site<select name="site_id" required>{farm.sites.map((item) => <option key={item.site_id} value={item.site_id}>{item.site_name}</option>)}</select></label><button>Assign node</button></form><p>NODE_01 / NODE_02 can only belong to demo farms. Real registered nodes cannot use their synthetic histories.</p></section>
    </fieldset>}
    <section className="mc-access"><h2>Register a node identifier</h2><form className="mc-admin-grid" onSubmit={(e) => perform(e, (data) => accessApi("/nodes", { method: "POST", body: { node_id: data.get("node_id"), sensor_metadata: data.get("sensor_metadata") || "Not supplied", calibration_reference: data.get("calibration_reference") || null } }))}><label>Node ID<input name="node_id" pattern="[A-Za-z0-9_-]+" minLength={3} maxLength={40} required /></label><label>Sensor metadata<input name="sensor_metadata" maxLength={500} /></label><label>Calibration reference (if available)<input name="calibration_reference" maxLength={200} /></label><button disabled={busy}>Register identifier</button></form><p>Registration is not hardware authentication, ingestion or calibration. Non-demo nodes remain unavailable for forecasts until verified C1 history exists.</p></section>
  </main>;
}
