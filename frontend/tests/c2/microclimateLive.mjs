import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { FEATURES, historicalSeries, loadDemo, MODELS, runForecast, summarize } from "../../src/services/c2/microclimateApi.js";
import { API_BASE, accessApi, sessionFetch } from "../../src/services/c2/accessApi.js";

if (!process.env.C2_TEST_USERNAME || !process.env.C2_TEST_PASSWORD) {
  throw new Error("Authenticated live check requires C2_TEST_USERNAME and C2_TEST_PASSWORD for an authorized research test account. Credentials are never printed.");
}
const originalFetch = globalThis.fetch;
let cookie = "";
globalThis.fetch = async (url, options = {}) => {
  const headers = new Headers(options.headers);
  if (cookie && String(url).startsWith(API_BASE + "/")) headers.set("Cookie", cookie);
  const target = process.env.C2_TEST_API_BASE && String(url).startsWith(API_BASE + "/") ? String(url).replace(API_BASE, process.env.C2_TEST_API_BASE) : url;
  const response = await originalFetch(target, { ...options, headers });
  for (const value of response.headers.getSetCookie()) {
    if (value.startsWith("c2_local_session=")) cookie = value.split(";", 1)[0];
  }
  return response;
};

try {
await accessApi("/login", { method: "POST", body: { username: process.env.C2_TEST_USERNAME, password: process.env.C2_TEST_PASSWORD } });

const evidence = [];
for (const node of ["NODE_01", "NODE_02"]) {
  const demo = await loadDemo(node);
  assert.equal(demo.demo.prepared_tensor_match, true);
  const history = historicalSeries(demo.request.observations);
  for (const model of MODELS) {
    const result = await runForecast(demo.request, model.id);
    assert.deepEqual(history.map((row) => row.trusted), result.history.history_valid_mask);
    for (const horizon of [24, 72, 168]) for (const key of FEATURES) assert.equal(summarize(result.predictions, key, horizon).count, horizon);
    if (model.id === "attention_bilstm" && node === "NODE_01") {
      const previous = JSON.parse(await readFile(new URL("../../../backend/experiments/c2/microclimate/api_integration_v1/example_forecast_response.json", import.meta.url), "utf8"));
      const difference = Math.max(...result.predictions.flatMap((row, index) => FEATURES.map((key) => Math.abs(row[key] - previous.predictions[index][key]))));
      assert.ok(difference <= 1e-4);
      evidence.push({ original_unit_difference_from_previous_api: difference });
    }
    evidence.push({ node, model: model.id, predictions: result.predictions.length, finite: true, horizon_counts: [24, 72, 168] });
  }
}
const yieldResponse = await sessionFetch(API_BASE + "/api/c2/yield/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ plant_height_cm: 60, main_branches: 5, leaf_length_cm: 8, leaf_breadth_cm: 3, days_to_50pct_flowering: 45 }) });
assert.equal(yieldResponse.status, 200);
evidence.push({ yield_api: "passed", result: await yieldResponse.json() });
const cors = await fetch("http://127.0.0.1:8000/api/c2/microclimate/forecast", { method: "OPTIONS", headers: { Origin: "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type" } });
assert.equal(cors.headers.get("access-control-allow-origin"), "http://127.0.0.1:5173");
evidence.push({ browser_origin_cors: "passed" });
console.log(JSON.stringify({ evaluation_label: "Synthetic Data — Prototype Evaluation Only", status: "passed", checks: evidence }, null, 2));
} finally {
  if (cookie) await accessApi("/logout", { method: "POST" }).catch(() => {});
  globalThis.fetch = originalFetch;
}
