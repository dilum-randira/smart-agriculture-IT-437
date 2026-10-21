import { MODELS, VARIABLES, summarize } from "../../../services/c2/microclimateApi";

export default function ComparisonResults({ comparison, horizon, node, activeModel }) {
  const rows = comparison.map((forecast) => ({ model: forecast.model, values: VARIABLES.map((variable) => summarize(forecast.predictions, variable.key, horizon)?.mean ?? null) }));
  const ranges = VARIABLES.map((variable, index) => {
    const values = rows.map((row) => row.values[index]).filter(Number.isFinite);
    return values.length ? { min: Math.min(...values), max: Math.max(...values), spread: Math.max(...values) - Math.min(...values) } : null;
  });
  return <div className="mc-comparison-results"><div className="mc-comparison-spreads" aria-label="Spread between model horizon means">{VARIABLES.map((variable, index) => <div className={variable.icon} key={variable.key}><span>{variable.name}</span><strong>{ranges[index] ? ranges[index].spread.toFixed(2) : "Unavailable"}<small>{variable.unit}</small></strong><p>Spread between model means</p></div>)}</div><div className="mc-table-wrap"><table><caption>{node} · Whole {horizon}-hour horizon, independent of day selection</caption><thead><tr><th scope="col">Forecast model</th>{VARIABLES.map((variable) => <th scope="col" key={variable.key}>{variable.name}<small>{variable.unit}</small></th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row.model} data-active={row.model === activeModel}><th scope="row">{MODELS.find((model) => model.id === row.model)?.name || row.model}{row.model === activeModel && <span className="mc-selected-model">Selected model</span>}</th>{row.values.map((value, index) => {
    const range = ranges[index];
    const position = range && Number.isFinite(value) ? range.spread ? (value - range.min) / range.spread * 100 : 50 : null;
    return <td key={VARIABLES[index].key}>{Number.isFinite(value) ? value.toFixed(2) : "Unavailable"}{position !== null && <div className={`mc-relative-mean ${VARIABLES[index].icon}`} role="img" aria-label={range.spread ? `Relative mean position: ${position.toFixed(0)} percent of this model comparison range; not an accuracy score` : "Equal model means; not an accuracy score"}><span style={{ left: `${position}%` }} /></div>}</td>;
  })}</tr>)}</tbody></table></div><p className="mc-comparison-note">Markers show relative horizon means, not model accuracy. Without future ground truth, no best-model ranking is inferred.</p></div>;
}
