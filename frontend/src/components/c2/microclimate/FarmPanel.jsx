import { Component, lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import ClimateIcon from "./ClimateIcon";
import Asset from "../../ui/Asset";
const FarmScene = lazy(() => import("./FarmScene"));

export function StaticFarm() {
  return <div className="mc-static-farm"><Asset name="farmScene" width={640} height={320} alt="Static conceptual farm diagram; illustrated open-field layout, not an installed physical farm" /><span className="mc-fallback-label">Conceptual sample layout · NODE_01 / NODE_02<br />Static illustration · Interactive 3D remains available</span></div>;
}

class SceneBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <StaticFarm /> : this.props.children; }
}

export default function FarmPanel({ node, onNodeChange, allowedNodes }) {
  const host = useRef(null);
  const [near, setNear] = useState(false);
  const [staticView, setStaticView] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [fullscreenError, setFullscreenError] = useState("");
  const fallback = useCallback(() => setUnavailable(true), []);
  const expand = useCallback(() => {
    const element = host.current;
    if (!element) return;
    setFullscreenError("");
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => setFullscreenError("Fullscreen view could not be closed."));
    } else {
      element.requestFullscreen?.().catch(() => setFullscreenError("Fullscreen view is unavailable in this browser."));
    }
  }, []);
  useEffect(() => {
    if (!("IntersectionObserver" in window)) { setNear(true); return undefined; }
    const observer = new IntersectionObserver(([entry]) => { if (entry.isIntersecting) { setNear(true); observer.disconnect(); } }, { rootMargin: "150px" });
    observer.observe(host.current); return () => observer.disconnect();
  }, []);
  return <section className="mc-farm-card" aria-labelledby="farm-heading" ref={host}>
    <div className="mc-panel-heading"><div><span className="mc-eyebrow">SPATIAL OVERVIEW</span><h2 id="farm-heading">The growing environment.</h2></div><span className="mc-focus-node"><span />{node || "Select a node"}</span></div>
    <div className="mc-farm-view">
      {near && !staticView && !unavailable ? <SceneBoundary><Suspense fallback={<StaticFarm />}><FarmScene node={node} onNodeChange={onNodeChange} allowedNodes={allowedNodes} onUnavailable={fallback} /></Suspense></SceneBoundary> : <StaticFarm />}
      <span className="mc-concept-badge"><ClimateIcon name="layers" size={15} />Interactive cultivation view</span>
    </div>
    <div className="mc-farm-caption"><span>{fullscreenError || (unavailable ? "3D unavailable. All forecasting features remain available." : staticView ? "Static cultivation illustration · No live sensor view" : "Drag to explore · Pinch or scroll to zoom")}</span><div><button type="button" onClick={expand} disabled={unavailable}>Expand view</button><button type="button" onClick={() => setStaticView((value) => !value)} disabled={unavailable}>{staticView ? "Enable 3D" : "Use static view"}</button></div></div>
    <p className="mc-farm-disclaimer">Conceptual pepper cultivation & sensor placement — not an installed IoT field. Node locations are illustrative; no live device connection is implied.</p>
  </section>;
}
