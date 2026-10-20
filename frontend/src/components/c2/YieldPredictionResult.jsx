import { yieldFields } from "../../services/c2/yieldApi";
import YieldIcon from "./YieldIcon";

export default function YieldPredictionResult({ result, pending, error, onEdit, onRetry, resultRef }) {
  const data = result?.data;
  return (
    <section className={`c2-card c2-result-card ${data ? "c2-result-ready" : ""}`} aria-labelledby="result-heading" aria-busy={pending}>
      <div className="c2-card-heading">
        <span className="c2-icon-box"><YieldIcon name="chart" /></span>
        <div><h3 id="result-heading">Yield estimate</h3><p>A research perspective on your traits.</p></div>
        <span className="c2-small-badge">02 / RESULT</span>
      </div>
      <div className="c2-result-content" aria-live="polite" aria-atomic="true">
        {pending ? (
          <div className="c2-empty-result" role="status">
            <div className="c2-result-emblem"><span className="c2-spinner" /></div>
            <h4>Connecting traits to yield</h4><p>Waiting for the prediction service to return your estimate.</p>
          </div>
        ) : error ? (
          <div className="c2-empty-result c2-error-result" role="alert">
            <div className="c2-result-emblem"><YieldIcon name="info" /></div>
            <h4>We couldn’t generate an estimate</h4><p>{error}</p>
            <button className="c2-button c2-button-outline" type="button" onClick={onRetry}>Try again <YieldIcon name="reset" /></button>
          </div>
        ) : data ? (
          <div className="c2-success-result" ref={resultRef} tabIndex={-1}>
            <span className="c2-eyebrow">EXPERIMENTAL TRAIT-BASED YIELD ESTIMATE</span>
            <div className="c2-yield-value">{data.predicted_yield_g_per_plant.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}<span>{data.unit}</span></div>
            <div className="c2-result-model"><YieldIcon name="check" /> {data.model}<span>Model output</span></div>
            <p className="c2-result-basis">Fresh / dry yield basis is not verified. This value is not a validated Sri Lankan fresh-yield forecast.</p>
            <h4 className="c2-summary-title">Submitted measurements</h4>
            <dl className="c2-measurement-summary">{yieldFields.map(({ key, label, unit }) => (
              <div key={key}><dt>{label}</dt><dd>{result.measurements[key]} <span>{unit}</span></dd></div>
            ))}</dl>
            <details className="c2-response-details"><summary>Research note & API metadata</summary>
              <p>{data.warning}</p>
              <dl><dt>Prediction type</dt><dd>{data.prediction_type}</dd><dt>Weight basis</dt><dd>{data.yield_weight_basis}</dd></dl>
            </details>
            <button type="button" className="c2-edit-link" onClick={onEdit}>Modify measurements <YieldIcon name="arrow" /></button>
          </div>
        ) : (
          <div className="c2-empty-result">
            <div className="c2-result-emblem"><YieldIcon name="leaf" /></div>
            <h4>Your next insight starts here.</h4>
            <p>Add your plant measurements and generate an estimate to see the model’s output.</p>
            <div className="c2-empty-steps"><span>Measure</span><i /><span>Estimate</span><i /><span>Explore</span></div>
          </div>
        )}
      </div>
      <div className="c2-result-footer"><YieldIcon name="info" /><span>A model estimate, not a harvest guarantee. <a href="#yield-limitations">Read the limitations ↗</a></span></div>
    </section>
  );
}
