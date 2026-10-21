import { API_BASE, sessionFetch } from "./accessApi.js";
export const SYNTHETIC_LABEL = "Synthetic Data — Prototype Evaluation Only";
export const FEATURES = ["soil_moisture_avg_index", "air_temperature_c", "relative_humidity_pct"];
export const MODELS = [
  { id: "attention_bilstm", name: "Attention BiLSTM", detail: "Attention-based bidirectional sequence model" },
  { id: "lstm", name: "LSTM", detail: "Long short-term memory baseline" },
  { id: "gru", name: "GRU", detail: "Gated recurrent unit baseline" },
];
export const VARIABLES = [
  { key: FEATURES[1], name: "Air temperature", unit: "°C", color: "#bc6031", icon: "temperature" },
  { key: FEATURES[2], name: "Relative humidity", unit: "%", color: "#347d9b", icon: "humidity" },
  { key: FEATURES[0], name: "Soil moisture", unit: "INDEX", color: "#357456", icon: "soil" },
];
const base = API_BASE;

export function isTrusted(row) {
  return row.record_status !== "INVALID" && !row.is_anomaly && !row.is_imputed;
}

/** Mirror the API's bounded causal fill for display only; the server remains authoritative. */
export function historicalSeries(observations) {
  let last = null;
  return observations.map((row) => {
    const trusted = isTrusted(row);
    if (trusted) last = Object.fromEntries(FEATURES.map((key) => [key, row[key]]));
    return { ...row, ...(last || {}), kind: trusted ? "Historical input" : "Causally filled input", trusted };
  });
}

export function summarize(predictions, key, horizon) {
  const values = predictions.slice(0, horizon).map((row) => row[key]);
  if (!values.length || values.some((value) => !Number.isFinite(value))) return null;
  return { mean: values.reduce((sum, value) => sum + value, 0) / values.length,
    min: Math.min(...values), max: Math.max(...values), count: values.length };
}

export function validateForecast(data, request) {
  const origin = Date.parse(request.observations.at(-1).timestamp);
  if (data?.model !== request.model || data?.node_id !== request.node_id ||
      data?.evaluation_label !== SYNTHETIC_LABEL || Date.parse(data.forecast_origin) !== origin ||
      !Array.isArray(data.predictions) || data.predictions.length !== 168 ||
      JSON.stringify(data.target_order) !== JSON.stringify(FEATURES) ||
      JSON.stringify(data.feature_order) !== JSON.stringify(FEATURES) ||
      data.units?.soil_moisture_avg_index !== "INDEX (not calibrated volumetric water content)" ||
      data.units?.air_temperature_c !== "°C" || data.units?.relative_humidity_pct !== "% RH" ||
      ![24, 72, 168].every((hours) => data.slices?.some((slice) => slice.hours === hours &&
        slice.start_index === 0 && slice.end_index_exclusive === hours &&
        Date.parse(slice.first_timestamp) === origin + 3600000 && Date.parse(slice.last_timestamp) === origin + hours * 3600000)) ||
      !data.predictions.every((row, index) => row.lead_hour === index + 1 &&
        Date.parse(row.timestamp) === origin + (index + 1) * 3600000 && FEATURES.every((key) => Number.isFinite(row[key])))) {
    throw new Error("The forecast response does not match the expected 336-to-168-hour contract.");
  }
  return data;
}

async function api(path, { signal, body, timeoutMs = 180000 } = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  let timedOut = false;
  if (signal?.aborted) abort();
  signal?.addEventListener("abort", abort, { once: true });
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  try {
    const response = await sessionFetch(base + path, {
      method: body ? "POST" : "GET", signal: controller.signal,
      ...(body ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 422) throw new Error("This historical window could not be accepted. Check the selected node and input quality.");
      if (response.status === 503) throw new Error("The frozen model is unavailable. Check that the backend experiment artifacts are present.");
      throw new Error("The forecast service could not complete this request. Please try again.");
    }
    if (!data) throw new Error("The forecast service returned an unreadable response.");
    return data;
  } catch (error) {
    if (timedOut) throw new Error("The request timed out. The first model load can take longer; please try again.");
    if (controller.signal.aborted) throw new DOMException("Request cancelled", "AbortError");
    if (error instanceof TypeError) throw new Error("Cannot reach the local backend. Start FastAPI on port 8000 and try again.");
    throw error;
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", abort);
  }
}

export async function loadDemo(node, { signal } = {}) {
  const query = new URLSearchParams({ node_id: node, model: "attention_bilstm", sample_index: "0" });
  const data = await api(`/api/c2/microclimate/demo-input?${query}`, { signal });
  const rows = data?.request?.observations;
  if (data?.evaluation_label !== SYNTHETIC_LABEL || data?.request?.node_id !== node ||
      data?.request?.data_origin !== "synthetic" || !Array.isArray(rows) || rows.length !== 336 ||
      !isTrusted(rows[0]) || !rows.every((row, index) => Number.isFinite(Date.parse(row.timestamp)) &&
        FEATURES.every((key) => Number.isFinite(row[key])) && (!index || Date.parse(row.timestamp) - Date.parse(rows[index - 1].timestamp) === 3600000))) {
    throw new Error("The demo input does not match the historical data contract.");
  }
  return data;
}

export async function runForecast(demoRequest, model, { signal } = {}) {
  const request = { ...demoRequest, model };
  return validateForecast(await api("/api/c2/microclimate/forecast", { signal, body: request }), request);
}

export const formatTime = (value, full = false) => new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Colombo", day: "2-digit", month: "short", ...(full ? { year: "numeric" } : {}),
  hour: "2-digit", minute: "2-digit", hourCycle: "h23",
}).format(new Date(value));
