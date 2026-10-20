import { useState } from "react";
import { benchmarks } from "../../services/c2/yieldResearch";

const metrics = {
  mae: { label: "MAE", unit: "g/plant", direction: "Lower is better", description: "Mean absolute error: the average absolute difference between predicted and observed yield." },
  rmse: { label: "RMSE", unit: "g/plant", direction: "Lower is better", description: "Root mean squared error: a measure of prediction error that gives more weight to larger misses." },
  r2: { label: "R²", unit: "", direction: "Higher is better", description: "R² measures explained variation. A value near zero indicates limited explanatory performance; negative values can occur." },
};

export default function YieldModelComparison() {
  const [metric, setMetric] = useState("mae");
  const selected = metrics[metric];
  const max = Math.max(...benchmarks.map((row) => row[metric]));
  const min = Math.min(0, ...benchmarks.map((row) => row[metric]));
  const range = max - min;
  const zero = -min / range * 100;
  return (
    <section className="c2-card c2-evidence-card" aria-labelledby="benchmark-heading">
      <div className="c2-section-kicker"><span>MODEL BENCHMARKS</span><span className="c2-dot-label">Held-out test</span></div>
      <h3 id="benchmark-heading">The evidence, side by side.</h3>
      <p className="c2-card-intro">54 records · 18 unseen genotypes. A shared test for every model.</p>
      <div className="c2-chart-toolbar">
        <div className="c2-segmented" role="group" aria-label="Comparison metric">
          {Object.entries(metrics).map(([key, item]) => <button type="button" key={key} aria-pressed={metric === key} onClick={() => setMetric(key)}>{item.label}</button>)}
        </div>
        <span>{selected.direction}</span>
      </div>
      <div className="c2-benchmark-chart" role="img" aria-label={`${selected.label} comparison. ${selected.direction}. ${benchmarks.map((row) => `${row.model}: ${row[metric].toFixed(3)} ${selected.unit}`).join("; ")}`}>
        {benchmarks.map((row) => (
          <div className="c2-benchmark-row" key={row.model}>
            <div className="c2-bar-label"><span>{row.model}{row.model === "SVR" && <small>Best on test</small>}</span><strong>{row[metric].toFixed(3)}</strong></div>
            <div className="c2-bar-track">
              <span className={`c2-bar c2-bar-${row.model === "Tuned XGBoost" ? "primary" : row.model === "SVR" ? "best" : row.model === "Training Mean" ? "reference" : "baseline"}`} style={{ left: `${row[metric] < 0 ? 0 : zero}%`, width: `${Math.abs(row[metric]) / range * 100}%` }} />
              {metric === "r2" && <span className="c2-zero-line" style={{ left: `${zero}%` }} />}
            </div>
          </div>
        ))}
        <div className="c2-chart-scale"><span>{min.toFixed(metric === "r2" ? 3 : 0)}</span><span>{selected.label} {selected.unit && `(${selected.unit})`}</span><span>{max.toFixed(3)}</span></div>
      </div>
      <p className="c2-metric-definition" aria-live="polite">{selected.description}</p>
      <div className="c2-evidence-note"><strong>Research candidate ≠ best test result.</strong> Tuned XGBoost is the planned primary candidate. SVR performed best on this preliminary test; Random Forest and SVR are learned baselines. Training Mean is the simple reference.</div>
      <details className="c2-data-details"><summary>View all metrics & source</summary>
        <div className="c2-table-scroll"><table><caption>Final held-out test metrics</caption><thead><tr><th scope="col">Model</th><th scope="col">MAE (g/plant)</th><th scope="col">RMSE (g/plant)</th><th scope="col">R²</th></tr></thead><tbody>{benchmarks.map((row) => <tr key={row.model}><th scope="row">{row.model}</th><td>{row.mae.toFixed(3)}</td><td>{row.rmse.toFixed(3)}</td><td>{row.r2.toFixed(3)}</td></tr>)}</tbody></table></div>
        <p>Source: <code>yield_final_test_metrics.csv</code> from the C2 experiment outputs. Static aggregate snapshot, not a live evaluation.</p>
      </details>
    </section>
  );
}
