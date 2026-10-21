import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { accessApi } from "../../../services/c2/accessApi";
import { useAuth } from "../../../auth/AuthProvider";
import "../../../styles/c2/access.css";

import { firstFarmSelection as firstSelection, assignedFarmSelection } from "../../../services/c2/farmSelection";
export function useFarmAccess() {
  const { user } = useAuth();
  const [farms, setFarms] = useState([]);
  const mode = "farm";
  const [revision, setRevision] = useState(0);
  const selectionRef = useRef({});
  const ownerRef = useRef(user.id);
  const [selection, setSelection] = useState({ farmId: "", siteId: "", nodeId: "" });
  const [accessError, setAccessError] = useState("");
  const [accessBusy, setAccessBusy] = useState(false);
  selectionRef.current = selection;
  useEffect(() => {
    const controller = new AbortController();
    if (ownerRef.current !== user.id) { ownerRef.current = user.id; selectionRef.current = {}; setFarms([]); setSelection(firstSelection(null)); }
    setAccessBusy(true); setAccessError("");
    accessApi("/farms", { signal: controller.signal }).then((data) => {
      if (controller.signal.aborted) return;
      const next = assignedFarmSelection(data, selectionRef.current);
      setFarms(next.farms); setSelection(next.selection);
    }).catch((error) => { if (!controller.signal.aborted) setAccessError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setAccessBusy(false); });
    return () => controller.abort();
  }, [user.id, user.role, revision]);
  useEffect(() => {
    const refresh = () => setRevision((value) => value + 1);
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, []);
  const farm = mode === "farm" ? farms.find((item) => item.farm_id === selection.farmId) : null;
  const site = farm?.sites.find((item) => item.site_id === selection.siteId);
  const allowedNodes = site?.nodes.map((item) => item.node_id) || [];
  function chooseFarm(id) { setSelection(firstSelection(farms.find((item) => item.farm_id === id))); }
  function chooseSite(id) { const next = farm?.sites.find((item) => item.site_id === id); setSelection({ farmId: farm.farm_id, siteId: id, nodeId: next?.nodes[0]?.node_id || "" }); }
  function chooseNode(id) { if (allowedNodes.includes(id)) setSelection((old) => ({ ...old, nodeId: id })); }
  return { user, farms, mode, selection, farm, site, allowedNodes, chooseFarm, chooseSite, chooseNode, accessError, accessBusy, refreshFarms: () => setRevision((value) => value + 1) };
}

export function LocationPlot({ latitude, longitude }) {
  if (latitude === null || longitude === null || !Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
  const x = 15 + (longitude + 180) / 360 * 330, y = 15 + (90 - latitude) / 180 * 150;
  return <figure className="mc-location-plot"><svg viewBox="0 0 360 190" role="img" aria-label={`Coordinate locator: latitude ${latitude}, longitude ${longitude}. Supplied coordinates, not independently verified; not a field boundary map.`}>
    <rect x="15" y="15" width="330" height="150" rx="3" fill="#eef3e7" stroke="#a8b99c" />
    {[1, 2, 3, 4, 5].map((i) => <path key={i} d={`M${15 + i * 55} 15v150`} stroke="#c8d4bc" />)}{[1, 2, 3].map((i) => <path key={i} d={`M15 ${15 + i * 37.5}h330`} stroke="#c8d4bc" />)}
    <path d="M180 15v150M15 90h330" stroke="#90a67f" strokeDasharray="3 3" /><circle cx={x} cy={y} r="5" fill="#285d3b" stroke="white" strokeWidth="2" />
    <g fontSize="9" fill="#53694a"><text x="15" y="183">−180°</text><text x="175" y="183">0°</text><text x="317" y="183">180°</text><text x="17" y="12">90° N</text><text x="312" y="12">90° S at bottom</text></g>
  </svg><figcaption>Offline coordinate locator · Supplied location; verification pending. <a href={`https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=14/${latitude}/${longitude}`} target="_blank" rel="noreferrer">View supplied location on OpenStreetMap</a>. Coordinates are shared with the map service only when you open this link.</figcaption></figure>;
}

export const displayFarmName = (farm) => farm?.is_demo ? "Sample cultivation site" : farm?.farm_name || "";
export const displaySiteName = (site, farm) => farm?.is_demo ? site?.site_name?.replace(/^Synthetic site /, "Site · ") || "" : site?.site_name || "";

export default function FarmAccess({ access }) {
  const { user, farm, site, mode, selection } = access;
  return <section className="mc-access" aria-labelledby="access-heading"><div className="mc-rail-title"><span className="mc-control-number">01</span><h2 id="access-heading">Farm & observation node</h2></div>
    {user.role === "admin" && <div className="mc-access-actions"><Link to="/predictions/manage">Manage users, farms & nodes</Link></div>}
    {access.accessBusy && <p role="status">Loading assigned farms…</p>}
    {!access.accessBusy && !access.accessError && !access.farms.length && <p>No farms assigned to this account. Ask an Admin to open Farm management, choose the existing farm and assign your username. Creating an empty farm does not connect sample observations.</p>}
    {mode === "farm" && <><div className="mc-location-controls"><label>Farm<select value={selection.farmId} onChange={(event) => access.chooseFarm(event.target.value)}><option value="">Select an assigned farm</option>{access.farms.map((item) => <option key={item.farm_id} value={item.farm_id}>{displayFarmName(item)}</option>)}</select></label><label>Site<select value={selection.siteId} onChange={(event) => access.chooseSite(event.target.value)} disabled={!farm}><option value="">No site selected</option>{farm?.sites.map((item) => <option key={item.site_id} value={item.site_id}>{displaySiteName(item, farm)}</option>)}</select></label><label>Observation node<select value={selection.nodeId} onChange={(event) => access.chooseNode(event.target.value)} disabled={!site}><option value="">No node selected</option>{site?.nodes.map((item) => <option key={item.node_id}>{item.node_id}</option>)}</select></label></div>
    {farm && <details className="mc-location-details"><summary>Location & data provenance</summary><div className="mc-location-info"><div><h3>{farm.farm_name}</h3><p>{farm.district} · {farm.timezone} · {farm.crop_type}</p><p>{farm.is_demo ? "Sample Data — location not verified" : farm.latitude === null ? "No coordinates supplied" : `Supplied coordinates: ${farm.latitude}, ${farm.longitude} (unverified)`}</p><p>Farm {farm.farm_id} → Site {site?.site_id || "not selected"} → Node {selection.nodeId || "not assigned"}</p><p>Provenance: {farm.provenance}</p><p>Growth stage: {farm.growth_stage || "Not supplied"} · Metadata only.</p></div>{!farm.is_demo && <LocationPlot latitude={farm.latitude} longitude={farm.longitude} />}</div></details>}</>}
    {!farm && <p className="mc-location-hint">Your assignments determine which sites and observation histories are available.</p>}
    {access.accessError && <p role="alert" className="mc-error">Farm assignments could not be loaded. {access.accessError}</p>}
    <button type="button" className="mc-refresh-farms" disabled={access.accessBusy} onClick={access.refreshFarms}>Refresh farm assignments</button>
  </section>;
}
