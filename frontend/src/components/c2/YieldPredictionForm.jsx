import { yieldFields } from "../../services/c2/yieldApi";
import YieldIcon from "./YieldIcon";

export default function YieldPredictionForm({ values, errors, pending, onChange, onSubmit, onReset }) {
  return (
    <section className="c2-card c2-input-card" aria-labelledby="measurement-heading">
      <div className="c2-card-heading">
        <span className="c2-icon-box"><YieldIcon name="leaf" /></span>
        <div><h3 id="measurement-heading">Plant measurements</h3><p>Five traits. One experimental estimate.</p></div>
        <span className="c2-small-badge">01 / INPUT</span>
      </div>
      <form noValidate onSubmit={onSubmit} aria-busy={pending}>
        <fieldset disabled={pending} className="c2-fields">
          <legend className="c2-sr-only">Required plant measurements</legend>
          {yieldFields.map((field, index) => (
            <div key={field.key} className={`c2-field ${index === 4 ? "c2-field-wide" : ""}`}>
              <label htmlFor={field.key}>{field.label} <span aria-hidden="true">*</span></label>
              <div className={`c2-input-wrap ${errors[field.key] ? "c2-input-invalid" : ""}`}>
                <input
                  id={field.key} name={field.key} type="number" inputMode="decimal" step="any"
                  min={field.minimum} required placeholder="Enter value"
                  value={values[field.key]} onChange={(event) => onChange(field.key, event.target.value)}
                  aria-invalid={!!errors[field.key]}
                  aria-describedby={`${field.key}-hint${errors[field.key] ? ` ${field.key}-error` : ""}`}
                />
                <span>{field.unit}</span>
              </div>
              <p id={`${field.key}-hint`} className="c2-field-hint">{field.hint}</p>
              {errors[field.key] && <p id={`${field.key}-error`} className="c2-field-error">{errors[field.key]}</p>}
            </div>
          ))}
        </fieldset>
        <div className="c2-form-actions">
          <button className="c2-button c2-button-green" type="submit" disabled={pending}>
            {pending ? <><span className="c2-spinner" /> Calculating estimate…</> : <>Estimate yield <YieldIcon name="arrow" /></>}
          </button>
          <button className="c2-reset" type="button" onClick={onReset}><YieldIcon name="reset" />{pending ? "Cancel & reset" : "Reset"}</button>
        </div>
        <p className="c2-form-footnote">All fields are required. Use your measured traits; no sample values are prefilled.</p>
      </form>
    </section>
  );
}
