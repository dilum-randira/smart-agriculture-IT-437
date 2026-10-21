import { AssetIcon } from "../../ui/Asset";
import { formatForecastTimestamp } from "../../../services/c2/forecastDays";
import { summarize } from "../../../services/c2/microclimateApi";

export default function ForecastDays({ days, selectedDay, onSelect, horizon }) {
  if (!days.length) return null;
  const selected = days.find((day) => day.key === selectedDay);
  const totalHours = days.reduce((count, day) => count + day.count, 0);
  const start = selected?.start || days[0].start, end = selected?.end || days.at(-1).end;
  return <div className="mc-day-navigation">
    <div className="mc-day-heading"><div><h3><AssetIcon name="calendar" size={18} />Explore by calendar day</h3><p>Asia/Colombo (UTC+05:30) · Calendar days may contain fewer than 24 forecast hours.</p></div><span>{selected ? `${selected.count} hourly predictions` : `${totalHours} hourly predictions`}</span></div>
    <div className="mc-day-tabs" role="group" aria-label="Forecast calendar day">
      <button type="button" aria-pressed={!selected} onClick={() => onSelect(null)}><strong>All Days</strong><span>Complete {horizon}h horizon</span><span className="mc-day-all-caption"><AssetIcon name="calendar" size={22} /><span>{days.length} calendar dates</span><small>{totalHours} hourly values</small></span></button>
      {days.map((day) => {
        const temperature = summarize(day.rows, "air_temperature_c", day.count);
        const humidity = summarize(day.rows, "relative_humidity_pct", day.count);
        const soil = summarize(day.rows, "soil_moisture_avg_index", day.count);
        return <button type="button" key={day.key} aria-pressed={selected?.key === day.key} onClick={() => onSelect(day.key)}><strong>{day.weekday}</strong><span>{day.date}</span><span className="mc-day-values"><span><AssetIcon name="temperature" size={14} />{temperature ? `${temperature.min.toFixed(1)}–${temperature.max.toFixed(1)} °C` : "Unavailable"}</span><span><AssetIcon name="humidity" size={14} />{humidity ? `${humidity.mean.toFixed(1)}% RH` : "Unavailable"}</span><span><AssetIcon name="soil" size={14} />{soil ? `${soil.mean.toFixed(1)} INDEX` : "Unavailable"}</span></span><small>{day.count} {day.count === 1 ? "hour" : "hours"}{day.partial ? " · Partial day" : ""}</small></button>;
      })}
    </div>
    <p className="mc-day-range" role="status">{selected ? `${selected.weekday} · ` : "All Days · "}<time dateTime={start}>{formatForecastTimestamp(start)}</time><span> → </span><time dateTime={end}>{formatForecastTimestamp(end)}</time></p>
  </div>;
}
