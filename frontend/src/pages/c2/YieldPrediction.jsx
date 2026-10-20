import { useEffect, useRef, useState } from "react";
import YieldHero from "../../components/c2/YieldHero";
import YieldPredictionForm from "../../components/c2/YieldPredictionForm";
import YieldPredictionResult from "../../components/c2/YieldPredictionResult";
import YieldModelComparison from "../../components/c2/YieldModelComparison";
import YieldExplainability from "../../components/c2/YieldExplainability";
import YieldIcon from "../../components/c2/YieldIcon";
import { predictYield, validateMeasurements, yieldFields } from "../../services/c2/yieldApi";
import "../../styles/c2/yieldPrediction.css";

const emptyValues = () => Object.fromEntries(yieldFields.map(({ key }) => [key, ""]));

export default function YieldPrediction() {
  const [values, setValues] = useState(emptyValues);
  const [errors, setErrors] = useState({});
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const request = useRef(null);
  const resultRef = useRef(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => { if (result) resultRef.current?.focus({ preventScroll: true }); }, [result]);

  function changeValue(key, value) {
    setValues((previous) => ({ ...previous, [key]: value }));
    setErrors((previous) => ({ ...previous, [key]: undefined }));
    setError("");
    setResult(null);
  }
  function reset() {
    request.current?.abort();
    request.current = null;
    setValues(emptyValues());
    setErrors({});
    setError("");
    setResult(null);
    setPending(false);
    document.getElementById(yieldFields[0].key)?.focus();
  }
  async function submit(event) {
    event?.preventDefault();
    if (request.current) return;
    const nextErrors = validateMeasurements(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      document.getElementById(Object.keys(nextErrors)[0])?.focus();
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    setPending(true);
    setResult(null);
    setError("");
    const measurements = Object.fromEntries(yieldFields.map(({ key }) => [key, Number(values[key])]));
    try {
      const data = await predictYield(measurements, { signal: controller.signal });
      if (request.current === controller) setResult({ data, measurements });
    } catch (failure) {
      if (request.current === controller && failure.name !== "AbortError") {
        setError(failure.message);
        setErrors(failure.fieldErrors || {});
      }
    } finally {
      if (request.current === controller) { request.current = null; setPending(false); }
    }
  }
  return (
    <main className="c2-yield">
      <div className="c2-page-top"><span>RESEARCH / <strong>YIELD PREDICTION</strong></span><span className="c2-prototype"><YieldIcon name="flask" /> Research prototype</span></div>
      <YieldHero />
      <div className="c2-overview-strip" aria-label="Research overview">
        <div><span className="c2-overview-number">05</span><span><strong>Measured plant traits</strong><small>The inputs behind each estimate</small></span></div>
        <div><YieldIcon name="chart" /><span><strong>Tuned XGBoost</strong><small>Primary research candidate</small></span></div>
        <div><YieldIcon name="leaf" /><span><strong>Transparent by design</strong><small>Benchmarks & global explanations</small></span></div>
      </div>

      <section id="yield-estimator" className="c2-page-section" aria-labelledby="estimator-heading">
        <div className="c2-section-heading"><div><span className="c2-eyebrow">FROM MEASUREMENT TO INSIGHT</span><h2 id="estimator-heading">Explore your plant’s potential.</h2></div><span className="c2-section-subtitle">Trait-based research · no live sensor data</span></div>
        <div className="c2-estimator-grid">
          <YieldPredictionForm values={values} errors={errors} pending={pending} onChange={changeValue} onSubmit={submit} onReset={reset} />
          <YieldPredictionResult result={result} resultRef={resultRef} error={error} pending={pending} onRetry={submit} onEdit={() => document.getElementById(yieldFields[0].key)?.focus()} />
        </div>
      </section>

      <section id="yield-evidence" className="c2-page-section" aria-labelledby="evidence-heading">
        <div className="c2-section-heading"><div><span className="c2-eyebrow">BEHIND THE PREDICTION</span><h2 id="evidence-heading">Good research shows its working.</h2></div><span className="c2-section-subtitle">Aggregate experiment outputs</span></div>
        <div className="c2-evidence-grid"><YieldModelComparison /><YieldExplainability /></div>
      </section>

      <section className="c2-limitations" id="yield-limitations" aria-labelledby="limitations-heading">
        <span className="c2-icon-box"><YieldIcon name="flask" /></span>
        <div><span className="c2-eyebrow">READ WITH CONTEXT</span><h2 id="limitations-heading">An estimate is a starting point.</h2>
          <p>This model was trained on published <i>Capsicum chinense</i> genotype-year trait aggregates. The fresh/dry yield basis is not explicitly verified, and the model has not been validated for Sri Lankan field-level fresh yield.</p>
          <p>It is not a future 7-day forecast or a live IoT prediction. The preliminary test scores indicate limited predictive performance. Use these outputs for research exploration; local field validation is needed before practical harvest or irrigation decisions.</p>
        </div>
        <span className="c2-limitations-tag">Experimental<br /><strong>by definition.</strong></span>
      </section>
      <div className="c2-page-signoff"><span>NAI MIRIS / C2 RESEARCH</span><span>Rooted in data. Open about uncertainty.</span></div>
    </main>
  );
}
