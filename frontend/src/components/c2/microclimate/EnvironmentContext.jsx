import { useState } from "react";
import FarmPanel, { StaticFarm } from "./FarmPanel";
import ClimateIcon from "./ClimateIcon";
import { displayFarmName, displaySiteName } from "./FarmAccess";
import { forecastVisualContext } from "../../../services/c2/forecastVisuals";

/** Optional context, deliberately secondary to forecast data and charts. */
export function EnvironmentView({ access, node, onNode, predictions, horizon, expanded, onToggle }) {
  const { tone } = forecastVisualContext(predictions, horizon);
  return <section id="environment-context" className={`mc-environment ${tone}`} aria-labelledby="environment-heading">
    <div className="mc-environment-intro"><div><p className="mc-eyebrow"><ClimateIcon name="layers" size={16} />SUPPORTING / INTERACTIVE 3D</p><h2 id="environment-heading">Your growing environment.</h2><p>Explore the conceptual cultivation layout and your selected observation node.</p><button type="button" className="mc-environment-toggle" aria-expanded={expanded} aria-controls="environment-detail" onClick={onToggle}>{expanded ? "Close environment view" : "Explore environment"}<span aria-hidden="true">{expanded ? "−" : "＋"}</span></button></div>{!expanded && <div className="mc-environment-preview" aria-hidden="true"><StaticFarm /></div>}</div>
    <div id="environment-detail" className="mc-environment-detail" hidden={!expanded}>{expanded && <><div className="mc-environment-copy"><span className="mc-context-pill">Supporting visual · Not live telemetry</span><h3>{displayFarmName(access.farm) || "Your cultivation context"}</h3><dl><dt>Selected site</dt><dd>{displaySiteName(access.site, access.farm) || "No site selected"}</dd><dt>Focused node</dt><dd>{node || "No node selected"}</dd></dl><p>The scene is illustrative. Node positions are not surveyed coordinates, and animation does not indicate current field conditions.</p><p>Forecasts remain based on the selected node’s historical inputs. The visual does not change model values.</p></div><FarmPanel node={node} onNodeChange={onNode} allowedNodes={access.allowedNodes} /></>}</div>
  </section>;
}

export default function EnvironmentContext(props) {
  const [expanded, setExpanded] = useState(true);
  return <EnvironmentView {...props} expanded={expanded} onToggle={() => setExpanded((value) => !value)} />;
}
