import test, { afterEach } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { FEATURES, historicalSeries, isTrusted, loadDemo, MODELS, runForecast, summarize, SYNTHETIC_LABEL, validateForecast, formatTime } from "../../src/services/c2/microclimateApi.js";

const artifact = "../../../backend/experiments/c2/microclimate/api_integration_v1/";
const request = JSON.parse(await readFile(new URL(artifact + "demo_request_NODE_01.json", import.meta.url), "utf8"));
const forecast = JSON.parse(await readFile(new URL(artifact + "example_forecast_response.json", import.meta.url), "utf8"));
const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
const json = (value, status = 200) => new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });

test("keeps trained feature order and exactly the three supported models", () => {
  assert.deepEqual(FEATURES, ["soil_moisture_avg_index", "air_temperature_c", "relative_humidity_pct"]);
  assert.deepEqual(MODELS.map((m) => m.id).sort(), ["attention_bilstm", "gru", "lstm"]);
  assert.equal(validateForecast(forecast, request), forecast);
});
test("retains the original quality policy, including usable clean WARN", () => {
  assert.equal(isTrusted({ record_status: "WARN", is_anomaly: false, is_imputed: false }), true);
  for (const row of [{ record_status: "INVALID" }, { is_anomaly: true }, { is_imputed: true }]) assert.equal(isTrusted(row), false);
});
test("historical chart uses causal filling without changing source observations", () => {
  const rows = structuredClone(request.observations), before = structuredClone(rows);
  const plotted = historicalSeries(rows);
  assert.deepEqual(rows, before);
  for (let i = 0; i < rows.length; i++) {
    assert.equal(plotted[i].timestamp, rows[i].timestamp);
    assert.equal(plotted[i].trusted, isTrusted(rows[i]));
    if (!isTrusted(rows[i])) {
      assert.equal(plotted[i].kind, "Causally filled input");
      for (const key of FEATURES) assert.equal(plotted[i][key], plotted[i - 1][key]);
    }
  }
  assert.deepEqual(plotted.map((row) => row.trusted), forecast.history.history_valid_mask);
});
test("forecast summaries use only the selected cumulative horizon and actual returned values", () => {
  for (const horizon of [24, 72, 168]) for (const key of FEATURES) {
    const values = forecast.predictions.slice(0, horizon).map((row) => row[key]);
    assert.deepEqual(summarize(forecast.predictions, key, horizon), {
      mean: values.reduce((a, b) => a + b, 0) / horizon, min: Math.min(...values), max: Math.max(...values), count: horizon,
    });
  }
  assert.equal(summarize([], FEATURES[0], 24), null);
});
test("rejects malformed output counts, reordered targets, incorrect units and broken slice boundaries", () => {
  for (const corrupt of [
    (data) => data.predictions.pop(), (data) => data.target_order.reverse(),
    (data) => data.feature_order.reverse(), (data) => { data.units.soil_moisture_avg_index = "% VWC"; },
    (data) => { data.slices[0].end_index_exclusive = 25; },
    (data) => { data.evaluation_label = "Field validated"; },
  ]) {
    const data = structuredClone(forecast); corrupt(data);
    assert.throws(() => validateForecast(data, request), /contract/);
  }
});
test("rejects future timestamps with gaps, overlaps or incorrect lead hours", () => {
  for (const corrupt of [
    (data) => { data.predictions[0].timestamp = request.observations.at(-1).timestamp; },
    (data) => { data.predictions[20].timestamp = data.predictions[19].timestamp; },
    (data) => { data.predictions[1].lead_hour = 3; },
  ]) { const data = structuredClone(forecast); corrupt(data); assert.throws(() => validateForecast(data, request), /contract/); }
});
test("rejects nonfinite original-unit predictions and node/model mismatches", () => {
  for (const value of [NaN, Infinity, null]) {
    const data = structuredClone(forecast); data.predictions[0].air_temperature_c = value;
    assert.throws(() => validateForecast(data, request), /contract/);
  }
  assert.throws(() => validateForecast({ ...forecast, node_id: "NODE_02" }, request), /contract/);
  assert.throws(() => validateForecast({ ...forecast, model: "gru" }, request), /contract/);
});
test("loads genuine demo history through the API without requesting future ground truth", async () => {
  let called;
  globalThis.fetch = async (url, options) => { called = { url, options }; return json({ request, evaluation_label: SYNTHETIC_LABEL }); };
  const demo = await loadDemo("NODE_01");
  assert.equal(called.options.method, "GET");
  assert.match(called.url, /demo-input\?.*node_id=NODE_01/);
  assert.equal(demo.request.observations.length, 336);
  assert.equal("y" in demo.request, false);
});
test("demo loader rejects wrong node, insufficient history, gaps and leading untrusted input", async () => {
  for (const corrupt of [
    (body) => { body.node_id = "NODE_02"; }, (body) => body.observations.pop(),
    (body) => { body.observations[1].timestamp = body.observations[0].timestamp; },
    (body) => { body.observations[0].record_status = "INVALID"; },
  ]) {
    const body = structuredClone(request); corrupt(body);
    globalThis.fetch = async () => json({ request: body, evaluation_label: SYNTHETIC_LABEL });
    await assert.rejects(loadDemo("NODE_01"), /historical data contract/);
  }
});
test("sends historical original-unit observations and quality metadata unchanged", async () => {
  const snapshot = structuredClone(request);
  globalThis.fetch = async (url, options) => {
    assert.match(url, /\/forecast$/); assert.equal(options.method, "POST");
    const sent = JSON.parse(options.body);
    assert.equal(sent.model, "gru"); assert.deepEqual(sent.observations, snapshot.observations);
    assert.equal("predictions" in sent, false); assert.equal("y" in sent, false);
    return json({ ...forecast, model: "gru" });
  };
  assert.equal((await runForecast(request, "gru")).model, "gru");
  assert.deepEqual(request, snapshot);
});
test("handles unavailable backend and safe server errors without exposing internal details", async () => {
  globalThis.fetch = async () => { throw new TypeError("network"); };
  await assert.rejects(loadDemo("NODE_01"), /Cannot reach the local backend/);
  for (const status of [422, 500, 503]) {
    globalThis.fetch = async () => json({ detail: "C:/private/model/secret traceback" }, status);
    await assert.rejects(runForecast(request, request.model), (error) => !/private|traceback/.test(error.message));
  }
});
test("distinguishes cancellation and rejects malformed JSON", async () => {
  const controller = new AbortController(); controller.abort();
  globalThis.fetch = async (_url, { signal }) => { if (signal.aborted) throw new DOMException("aborted", "AbortError"); };
  await assert.rejects(loadDemo("NODE_01", { signal: controller.signal }), { name: "AbortError" });
  globalThis.fetch = async () => new Response("broken json", { status: 200 });
  await assert.rejects(loadDemo("NODE_01"), /unreadable/);
});
test("timestamps are displayed in Asia/Colombo independently of machine timezone", () => {
  assert.match(formatTime("2025-11-21T00:30:00Z"), /21 Nov.*06:00/);
});
