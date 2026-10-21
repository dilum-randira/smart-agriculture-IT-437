import { useId, useState } from "react";
import { forecastAxisLabel, formatForecastTimestamp, selectForecastDay } from "../../../services/c2/forecastDays";

export default function ForecastChart({ variable, history, predictions, horizon, origin, selectedDay = null }) {
  const id = useId().replace(/:/g, "");
  const [historyHours, setHistoryHours] = useState(336);
  const [cursor, setCursor] = useState(null);
  const historical = selectedDay ? [] : history.slice(-historyHours);
  const future = selectForecastDay(predictions, horizon, selectedDay);
  const points = [...historical, ...future.map((row) => ({ ...row, kind: "Forecast" }))];
  if (!points.length) return <div className="mc-chart-empty">{selectedDay ? "No predictions available for this calendar day in the selected horizon." : "Historical inputs will appear here when the local backend is connected."}</div>;
  const W = 900, H = 265, left = 54, right = 14, top = 18, bottom = 56;
  const values = points.map((p) => p[variable.key]);
  const low = Math.min(...values), high = Math.max(...values), pad = Math.max((high - low) * .16, .5);
  const min = low - pad, max = high + pad;
  const x = (index) => left + index / Math.max(points.length - 1, 1) * (W - left - right);
  const y = (value) => top + (1 - (value - min) / (max - min)) * (H - top - bottom);
  const path = (rows, offset) => rows.map((p, i) => `${i ? "L" : "M"}${x(offset + i).toFixed(2)},${y(p[variable.key]).toFixed(2)}`).join(" ");
  const forecastLine = future.length ? [...(historical.length ? [historical.at(-1)] : []), ...future] : [];
  const forecastOffset = Math.max(0, historical.length - 1);
  const active = cursor === null ? null : Math.min(cursor, points.length - 1);
  const selected = active === null ? null : points[active];
  const originX = x(forecastOffset);
  const inspected = selected || historical.at(-1) || points[0];
  const ticks = [...new Set([0, Math.round((points.length - 1) / 3), Math.round((points.length - 1) * 2 / 3), points.length - 1])];
  return <div className="mc-chart">
    <div className="mc-chart-tools"><span>{!selectedDay && <><i className="mc-key history" />Historical input </>}<i className="mc-key forecast" style={{ background: variable.color }} />Forecast{selectedDay ? ` · ${future.length} hourly values` : ""}</span>
      {!selectedDay && <label>History view <select aria-label={`${variable.name} history view`} value={historyHours} onChange={(e) => { setHistoryHours(Number(e.target.value)); setCursor(null); }}><option value={336}>14 days</option><option value={72}>3 days</option><option value={24}>24 hours</option></select></label>}</div>
    <div className="mc-chart-plot" onPointerLeave={() => setCursor(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby={`${id}-title ${id}-desc`} onPointerMove={(e) => {
        const box = e.currentTarget.getBoundingClientRect();
        setCursor(Math.max(0, Math.min(points.length - 1, Math.round(((e.clientX - box.left) / box.width * W - left) / (W - left - right) * (points.length - 1)))));
      }}>
        <title id={`${id}-title`}>{`${variable.name}: ${selectedDay ? `${future.length} hourly forecasts on ${selectedDay}` : `historical inputs and ${horizon}-hour forecast`}, ${variable.unit}`}</title>
        <desc id={`${id}-desc`}>Synthetic prototype. {selectedDay ? "Only the selected calendar day’s hourly forecasts are displayed." : "Solid muted history and colored dashed forecasts."} Times in Asia/Colombo. Use the point inspector below for exact values.</desc>
        <defs><linearGradient id={`${id}-fill`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={variable.color} stopOpacity=".13" /><stop offset="100%" stopColor={variable.color} stopOpacity="0" /></linearGradient></defs>
        {future.length > 0 && <rect x={originX} y={top} width={W - right - originX} height={H - top - bottom} fill={variable.color} opacity=".06" />}
        {[0, 1, 2, 3, 4].map((i) => { const value = min + (max - min) * i / 4; return <g key={i}><line x1={left} x2={W - right} y1={y(value)} y2={y(value)} stroke="#e4e8ed" strokeDasharray="3 5" /><text x={left - 10} y={y(value) + 4} textAnchor="end">{value.toFixed(1)}</text></g>; })}
        <path d={path(historical, 0)} fill="none" stroke="#8d9aa6" strokeWidth="1.7" />
        {historical.map((row, i) => row.trusted === false ? <circle key={row.timestamp} cx={x(i)} cy={y(row[variable.key])} r="2" fill="#a56e35"><title>{`Causally filled input: ${formatForecastTimestamp(row.timestamp)}`}</title></circle> : null)}
        {forecastLine.length > 0 && <><path d={`${path(forecastLine, forecastOffset)} L${x(points.length - 1)},${H - bottom} L${originX},${H - bottom} Z`} fill={`url(#${id}-fill)`} /><path d={path(forecastLine, forecastOffset)} fill="none" stroke={variable.color} strokeWidth="2.7" strokeDasharray="6 3" />{forecastLine.length === 1 && <circle cx={originX} cy={y(forecastLine[0][variable.key])} r="4" fill={variable.color} />}</>}
        {historical.length > 0 && <><line x1={originX} x2={originX} y1={top} y2={H - bottom} stroke="#465f7a" strokeDasharray="4 4" /><text x={Math.max(left + 36, Math.min(originX, W - 72))} y={top + 12} textAnchor="middle" className="mc-origin-label">Forecast origin</text></>}
        {future.length > 0 && <text x={W - right - 10} y={top + 31} textAnchor="end" className="mc-horizon-label">{future.length} hourly forecasts</text>}
        {ticks.map((index) => { const label = forecastAxisLabel(points[index].timestamp); return <text key={index} x={x(index)} y={H - 28} textAnchor={index === 0 ? "start" : index === points.length - 1 ? "end" : "middle"}><tspan x={x(index)}>{label.date}</tspan><tspan x={x(index)} dy="15">{label.time}</tspan></text>; })}
        {selected && <><line x1={x(active)} x2={x(active)} y1={top} y2={H - bottom} stroke="#678172" opacity=".7" /><circle cx={x(active)} cy={y(selected[variable.key])} r="4" fill={variable.color} stroke="white" strokeWidth="2"><title>{`${formatForecastTimestamp(selected.timestamp)}: ${selected[variable.key].toFixed(2)} ${variable.unit}`}</title></circle></>}
      </svg>
    </div>
    <div className="mc-inspector"><label htmlFor={`${id}-point`}>Inspect hourly value</label><input id={`${id}-point`} type="range" min="0" max={points.length - 1} value={active ?? Math.max(0, historical.length - 1)} onChange={(e) => setCursor(Number(e.target.value))} aria-valuetext={`${formatForecastTimestamp(inspected.timestamp)}: ${inspected[variable.key].toFixed(2)} ${variable.unit}`} />
      <output aria-live="polite">{selected || selectedDay ? <><b>{inspected[variable.key].toFixed(2)} {variable.unit}</b> · {inspected.kind} · {formatForecastTimestamp(inspected.timestamp)}</> : "Hover, touch or use the slider to inspect"}</output></div>
    <p className="mc-chart-note">Asia/Colombo (UTC+05:30) · {selectedDay ? "Selected calendar day only" : "Filled historical inputs marked in amber"} · {origin ? `Origin ${formatForecastTimestamp(origin)}` : "No forecast requested yet"}</p>
  </div>;
}
