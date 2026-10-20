import { featureImportance } from "../../services/c2/yieldResearch";

export default function YieldExplainability() {
  const max = Math.max(...featureImportance.map((feature) => feature.value));
  return (
    <section className="c2-card c2-evidence-card" aria-labelledby="explainability-heading">
      <div className="c2-section-kicker"><span>EXPLAINABLE AI</span><span className="c2-dot-label">Global SHAP</span></div>
      <h3 id="explainability-heading">What shapes the estimate?</h3>
      <p className="c2-card-intro">How strongly each trait contributes to tuned XGBoost predictions across development data.</p>
      <div className="c2-shap-chart" role="img" aria-label={`Global mean absolute SHAP values in g/plant: ${featureImportance.map((feature) => `${feature.label}: ${feature.value}`).join("; ")}.`}>
        {featureImportance.map((feature, index) => (
          <div className="c2-shap-row" key={feature.key}>
            <span className="c2-shap-rank">0{index + 1}</span>
            <div><div className="c2-bar-label"><span>{feature.label}</span><strong>{feature.value.toFixed(3)}</strong></div>
              <div className="c2-bar-track"><span className="c2-bar c2-bar-shap" style={{ width: `${feature.value / max * 100}%`, opacity: 1 - index * 0.12 }} /></div>
            </div>
          </div>
        ))}
      </div>
      <p className="c2-metric-definition">Mean absolute SHAP (g/plant). Larger values indicate greater average contribution magnitude, not whether a trait increases or decreases yield.</p>
      <div className="c2-evidence-note"><strong>Model explanations, not cause and effect.</strong> These are global explanations on development data, not personalized explanations for your submitted measurements.</div>
      <details className="c2-data-details"><summary>How to read this & source</summary>
        <p>SHAP assigns contributions to the model’s predictions. Taking their absolute values and averaging describes overall importance; it does not establish causal relationships or how changing a trait would affect a real plant.</p>
        <p>Source: <code>shap_feature_importance.csv</code> from the C2 experiment outputs. Values are rounded to three decimals for display.</p>
      </details>
    </section>
  );
}
