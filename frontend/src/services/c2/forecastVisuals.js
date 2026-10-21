import { summarize } from "./microclimateApi.js";

/** Presentation cues, not weather classes, agronomic thresholds or risk advice. */
export function forecastVisualContext(rows, horizon) {
  const temperature = summarize(rows, "air_temperature_c", horizon);
  const humidity = summarize(rows, "relative_humidity_pct", horizon);
  if (!temperature || !humidity) return { tone: "neutral", label: "Your outlook is ready to explore", temperature: null, humidity: null };
  const tone = humidity.mean >= 80 ? "humid" : temperature.mean >= 32 ? "warm" : "temperate";
  return { tone, label: tone === "humid" ? "Humidity in focus" : tone === "warm" ? "Temperature in focus" : "A view of the growing environment", temperature, humidity };
}

/** An exact display polyline from supplied values; no forecast smoothing or new data. */
export function sparklinePoints(rows, key, width = 240, height = 48) {
  const values = rows.map((row) => row[key]);
  if (!values.length || !values.every(Number.isFinite)) return "";
  const min = Math.min(...values), span = Math.max(...values) - min;
  return values.map((value, index) => `${(index / Math.max(1, values.length - 1) * width).toFixed(2)},${(span ? 4 + (1 - (value - min) / span) * (height - 8) : height / 2).toFixed(2)}`).join(" ");
}
