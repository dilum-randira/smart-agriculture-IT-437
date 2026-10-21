import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { forecastVisualContext, sparklinePoints } from "../../src/services/c2/forecastVisuals.js";
import { summarize } from "../../src/services/c2/microclimateApi.js";

const artifact = JSON.parse(await readFile(new URL("../../../backend/experiments/c2/microclimate/api_integration_v1/example_forecast_response.json", import.meta.url), "utf8"));

test("environmental hero uses actual horizon means and never alters API rows", () => {
  const before = structuredClone(artifact.predictions);
  for (const horizon of [24, 72, 168]) {
    const context = forecastVisualContext(artifact.predictions, horizon);
    assert.deepEqual(context.temperature, summarize(artifact.predictions, "air_temperature_c", horizon));
    assert.deepEqual(context.humidity, summarize(artifact.predictions, "relative_humidity_pct", horizon));
    assert.ok(!/rain|cloud|sunny|risk|stress|live/i.test(context.label));
    assert.equal("rainfall" in context, false);
  }
  assert.deepEqual(artifact.predictions, before);
});

test("no data produces no invented measurements or trends", () => {
  const context = forecastVisualContext([], 24);
  assert.equal(context.tone, "neutral"); assert.equal(context.temperature, null); assert.equal(context.humidity, null);
  assert.equal(sparklinePoints([], "air_temperature_c"), "");
});

test("visual tones are presentation-only temperature and humidity cues", () => {
  // These are unit fixtures for style decisions, not displayed field measurements.
  for (const [air_temperature_c, relative_humidity_pct, tone] of [[34, 60, "warm"], [27, 85, "humid"], [27, 65, "temperate"]]) {
    assert.equal(forecastVisualContext([{ air_temperature_c, relative_humidity_pct }], 24).tone, tone);
  }
});

test("sparklines retain one point per actual returned hour without smoothing or padding", () => {
  for (const key of artifact.target_order) {
    const rows = artifact.predictions.slice(0, 24);
    const points = sparklinePoints(rows, key).split(" ").map((point) => point.split(",").map(Number));
    assert.equal(points.length, rows.length);
    assert.ok(points.flat().every(Number.isFinite));
    assert.equal(points[0][0], 0); assert.equal(points.at(-1)[0], 240);
    const values = rows.map((row) => row[key]);
    assert.equal(points[values.indexOf(Math.max(...values))][1], 4);
    assert.equal(points[values.indexOf(Math.min(...values))][1], 44);
  }
});

test("constant and single-hour trends stay finite and unavailable values are not fabricated", () => {
  assert.equal(sparklinePoints([{ value: 7 }], "value"), "0.00,24.00");
  assert.equal(sparklinePoints([{ value: 7 }, { value: 7 }], "value"), "0.00,24.00 240.00,24.00");
  assert.equal(sparklinePoints([{ value: NaN }], "value"), "");
});
