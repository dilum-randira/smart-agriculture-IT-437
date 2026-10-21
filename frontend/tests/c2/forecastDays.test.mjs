import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { forecastDateKey, formatForecastTimestamp, forecastAxisLabel, groupForecastDays, selectForecastDay } from "../../src/services/c2/forecastDays.js";

const artifact = JSON.parse(await readFile(new URL("../../../backend/experiments/c2/microclimate/api_integration_v1/example_forecast_response.json", import.meta.url), "utf8"));
// Boundary fixtures contain timestamps only. Displayed prediction values come from the saved API response.
const hourly = (start, count) => Array.from({ length: count }, (_, index) => ({ timestamp: new Date(Date.parse(start) + index * 3600000).toISOString() }));

test("calendar dates use Colombo midnight, not UTC midnight", () => {
  assert.equal(forecastDateKey("2026-10-24T18:29:59Z"), "2026-10-24");
  assert.equal(forecastDateKey("2026-10-24T18:30:00Z"), "2026-10-25");
  assert.equal(forecastDateKey("2026-10-25T00:00:00+05:30"), "2026-10-25");
  assert.match(formatForecastTimestamp("2026-10-24T18:30:00Z"), /^Sunday, 25 Oct 2026.*00:00$/);
  const axis = forecastAxisLabel("2026-10-24T18:30:00Z");
  assert.match(axis.date, /^Sun,? 25 Oct$/); assert.equal(axis.time, "00:00");
});

test("24/72/168 hours can span 2/4/8 calendar dates with partial first and last days", () => {
  const rows = hourly("2026-10-25T23:00:00+05:30", 168);
  for (const [horizon, dayCount] of [[24, 2], [72, 4], [168, 8]]) {
    const groups = groupForecastDays(rows, horizon);
    assert.equal(groups.length, dayCount);
    assert.equal(groups[0].count, 1); assert.equal(groups[0].partial, true);
    assert.equal(groups.at(-1).count, 23); assert.equal(groups.at(-1).partial, true);
    assert.equal(groups.reduce((count, group) => count + group.count, 0), horizon);
    assert.deepEqual(groups.flatMap((group) => group.rows), rows.slice(0, horizon));
    assert.ok(groups.slice(1, -1).every((group) => !group.partial && group.count === 24));
  }
});

test("midnight-aligned horizons contain complete days without an extra day", () => {
  const rows = hourly("2026-10-25T00:00:00+05:30", 168);
  for (const horizon of [24, 72, 168]) {
    const groups = groupForecastDays(rows, horizon);
    assert.equal(groups.length, horizon / 24);
    assert.ok(groups.every((group) => group.count === 24 && !group.partial));
  }
});

test("calendar grouping handles month, year and leap-day transitions", () => {
  for (const [start, expected] of [
    ["2026-12-31T23:00:00+05:30", ["2026-12-31", "2027-01-01"]],
    ["2028-02-28T23:00:00+05:30", ["2028-02-28", "2028-02-29"]],
    ["2028-02-29T23:00:00+05:30", ["2028-02-29", "2028-03-01"]],
  ]) assert.deepEqual(groupForecastDays(hourly(start, 24), 24).map((group) => group.key), expected);
});

test("actual backend rows and all three target values are preserved for every day and horizon", () => {
  const before = structuredClone(artifact.predictions);
  for (const horizon of [24, 72, 168]) {
    const groups = groupForecastDays(artifact.predictions, horizon);
    assert.deepEqual(selectForecastDay(artifact.predictions, horizon), artifact.predictions.slice(0, horizon));
    for (const day of groups) {
      const selected = selectForecastDay(artifact.predictions, horizon, day.key);
      assert.deepEqual(selected, day.rows);
      assert.equal(day.start, selected[0].timestamp); assert.equal(day.end, selected.at(-1).timestamp);
      for (const row of selected) { assert.equal(row, artifact.predictions.find((item) => item.timestamp === row.timestamp)); assert.equal(forecastDateKey(row.timestamp), day.key); }
    }
  }
  assert.deepEqual(artifact.predictions, before);
});

test("horizon limits exclude future days without padding or inventing missing predictions", () => {
  const rows = hourly("2026-10-25T23:00:00+05:30", 168);
  assert.equal(selectForecastDay(rows, 24, "2026-10-27").length, 0);
  assert.equal(groupForecastDays(rows.slice(0, 1), 24)[0].count, 1);
  assert.deepEqual(groupForecastDays([], 168), []);
  assert.deepEqual(selectForecastDay([], 24), []);
  assert.throws(() => groupForecastDays(rows, 48), /horizon/);
});

test("invalid or timezone-naive timestamps cannot silently depend on the browser timezone", () => {
  for (const value of ["invalid", "2026-10-25T12:00:00", "2026-10-25", null]) assert.throws(() => forecastDateKey(value), /timezone offset/);
});

test("grouping and labels are identical in different host timezones", () => {
  const moduleURL = new URL("../../src/services/c2/forecastDays.js", import.meta.url).href;
  const script = `import {forecastDateKey,formatForecastTimestamp} from ${JSON.stringify(moduleURL)}; console.log(JSON.stringify([forecastDateKey('2026-10-24T18:30:00Z'),formatForecastTimestamp('2026-10-24T18:30:00Z')]));`;
  const outputs = ["UTC", "America/Los_Angeles", "Asia/Tokyo"].map((TZ) => execFileSync(process.execPath, ["--input-type=module", "-e", script], { env: { ...process.env, TZ }, encoding: "utf8" }).trim());
  assert.equal(new Set(outputs).size, 1);
  assert.match(outputs[0], /Sunday/);
});
