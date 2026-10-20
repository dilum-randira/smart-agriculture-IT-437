import test, { afterEach } from "node:test";
import assert from "node:assert/strict";
import { predictYield, validateMeasurements } from "../../src/services/c2/yieldApi.js";

const fetchOriginal = globalThis.fetch;
afterEach(() => { globalThis.fetch = fetchOriginal; });
// Test fixtures only. Never shipped to or prefilled in the application.
const values = { plant_height_cm: 65, main_branches: 5, leaf_length_cm: 10, leaf_breadth_cm: 5, days_to_50pct_flowering: 80 };
const responseFixture = { predicted_yield_g_per_plant: 123.45, model: "Test model", prediction_type: "experimental_trait_based_yield_estimate", yield_weight_basis: "not_verified_fresh_or_dry", unit: "g/plant", warning: "Test-only response." };

test("requires all five fields and rejects non-finite inputs", () => {
  assert.equal(Object.keys(validateMeasurements({})).length, 5);
  for (const bad of ["", " ", NaN, Infinity, "abc", null]) {
    assert.ok(validateMeasurements({ ...values, plant_height_cm: bad }).plant_height_cm);
  }
});
test("matches Pydantic bounds without inventing upper bounds or integer constraints", () => {
  assert.deepEqual(validateMeasurements({ plant_height_cm: 0, main_branches: 0.5, leaf_length_cm: 0, leaf_breadth_cm: 0, days_to_50pct_flowering: 0.1 }), {});
  assert.deepEqual(validateMeasurements({ ...values, plant_height_cm: 1e9 }), {});
  assert.ok(validateMeasurements({ ...values, days_to_50pct_flowering: 0 }).days_to_50pct_flowering);
  assert.ok(validateMeasurements({ ...values, main_branches: -1 }).main_branches);
});
test("sends exactly the five numeric features and returns the actual response", async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "http://127.0.0.1:8000/api/c2/yield/predict");
    assert.equal(options.method, "POST");
    assert.deepEqual(JSON.parse(options.body), values);
    return Response.json(responseFixture);
  };
  assert.deepEqual(await predictYield({ ...values, plant_height_cm: "65", unexpected: "omit" }), responseFixture);
});
test("does not send invalid measurements", async () => {
  globalThis.fetch = () => assert.fail("Must not fetch");
  await assert.rejects(predictYield({}), /highlighted measurements/);
});
test("maps API validation errors to the corresponding input", async () => {
  globalThis.fetch = async () => Response.json({ detail: [{ loc: ["body", "main_branches"], msg: "Invalid value" }] }, { status: 422 });
  await assert.rejects(predictYield(values), (error) => error.fieldErrors.main_branches === "Invalid value");
});
test("handles unavailable backend and server failure without exposing internals", async () => {
  globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };
  await assert.rejects(predictYield(values), /Cannot reach/);
  globalThis.fetch = async () => new Response("Private stack trace", { status: 500 });
  await assert.rejects(predictYield(values), /backend model service is ready/);
});
test("rejects malformed success, missing research metadata and wrong units", async () => {
  for (const data of [null, {}, { ...responseFixture, warning: "" }, { ...responseFixture, predicted_yield_g_per_plant: "123" }, { ...responseFixture, unit: "kg" }]) {
    globalThis.fetch = async () => Response.json(data);
    await assert.rejects(predictYield(values), /unexpected response/);
  }
});
test("timeout and explicit cancellation are distinguishable", async () => {
  globalThis.fetch = async (_url, { signal }) => new Promise((_resolve, reject) => {
    const abort = () => reject(new DOMException("Aborted", "AbortError"));
    if (signal.aborted) abort();
    else signal.addEventListener("abort", abort, { once: true });
  });
  await assert.rejects(predictYield(values, { timeoutMs: 5 }), /taking too long/);
  const controller = new AbortController();
  const pending = predictYield(values, { signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, { name: "AbortError" });
});
