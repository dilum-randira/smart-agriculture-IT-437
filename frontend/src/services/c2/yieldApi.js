import { API_BASE, sessionFetch } from "./accessApi.js";
export const yieldFields = [
  { key: "plant_height_cm", label: "Plant height", unit: "cm", hint: "Height from the plant base to its highest point.", minimum: 0 },
  { key: "main_branches", label: "Main branches", unit: "count", hint: "Number of main branches. Aggregate averages may be fractional.", minimum: 0 },
  { key: "leaf_length_cm", label: "Leaf length", unit: "cm", hint: "Length of the leaf blade, from base to tip.", minimum: 0 },
  { key: "leaf_breadth_cm", label: "Leaf breadth", unit: "cm", hint: "Width across the broadest part of the leaf.", minimum: 0 },
  { key: "days_to_50pct_flowering", label: "Days to 50% flowering", unit: "days", hint: "Days until half of the observed plants have flowered.", minimum: 0, exclusive: true },
];

export function validateMeasurements(values) {
  const errors = {};
  for (const field of yieldFields) {
    const raw = values[field.key];
    const number = Number(raw);
    if (raw === undefined || raw === null || String(raw).trim() === "") {
      errors[field.key] = `Enter ${field.label.toLowerCase()}.`;
    } else if (!Number.isFinite(number)) {
      errors[field.key] = "Enter a finite number.";
    } else if (field.exclusive ? number <= 0 : number < 0) {
      errors[field.key] = field.exclusive ? "Enter a number greater than zero." : "Enter zero or a positive number.";
    }
  }
  return errors;
}

export class YieldApiError extends Error {
  constructor(message, fieldErrors = {}) {
    super(message);
    this.name = "YieldApiError";
    this.fieldErrors = fieldErrors;
  }
}

const baseUrl = API_BASE;

export async function predictYield(values, { signal, timeoutMs = 30000 } = {}) {
  const errors = validateMeasurements(values);
  if (Object.keys(errors).length) throw new YieldApiError("Please check the highlighted measurements.", errors);
  const controller = new AbortController();
  let timedOut = false;
  const abort = () => controller.abort();
  if (signal?.aborted) abort();
  signal?.addEventListener("abort", abort, { once: true });
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  try {
    const response = await sessionFetch(`${baseUrl}/api/c2/yield/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(yieldFields.map(({ key }) => [key, Number(values[key])]))),
      signal: controller.signal,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 422 && Array.isArray(data?.detail)) {
        const fieldErrors = {};
        for (const detail of data.detail) {
          const key = detail.loc?.at(-1);
          if (yieldFields.some((field) => field.key === key)) fieldErrors[key] = detail.msg;
        }
        throw new YieldApiError("The API could not accept these measurements. Check your values and try again.", fieldErrors);
      }
      throw new YieldApiError(response.status >= 500
        ? "The prediction service could not complete this estimate. Please try again when the backend model service is ready."
        : `The prediction request was unsuccessful (${response.status}). Please try again.`);
    }
    if (!data || typeof data.predicted_yield_g_per_plant !== "number" ||
        !Number.isFinite(data.predicted_yield_g_per_plant) ||
        !["model", "prediction_type", "yield_weight_basis", "unit", "warning"].every((key) => typeof data[key] === "string" && data[key].trim()) ||
        data.unit !== "g/plant") {
      throw new YieldApiError("The service returned an unexpected response. No estimate has been displayed. Please check the backend version.");
    }
    return data;
  } catch (error) {
    if (timedOut) throw new YieldApiError("The prediction is taking too long. Please try again.");
    if (error.name === "AbortError" || error instanceof YieldApiError) throw error;
    throw new YieldApiError("Cannot reach the prediction service. Check your connection and that the FastAPI backend is running, then try again.");
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", abort);
  }
}
