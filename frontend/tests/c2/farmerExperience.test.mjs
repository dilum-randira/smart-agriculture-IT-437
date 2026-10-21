import test from "node:test";
import assert from "node:assert/strict";
import { farmSummary } from "../../src/services/c2/farmSummary.js";
import { canAccess, safeDestination } from "../../src/auth/policy.js";

test("farmer destinations are available without exposing administration", () => {
  for (const path of ["/farms", "/sensors", "/account", "/monitoring", "/predictions", "/predictions/microclimate"]) {
    assert.ok(canAccess("viewer", path)); assert.equal(safeDestination(path), path);
  }
  assert.equal(canAccess("viewer", "/predictions/manage"), false);
  assert.equal(canAccess("researcher", "/predictions/manage"), false);
});
test("new farm summary has no fabricated sensor data", () => {
  assert.deepEqual(farmSummary([{ sites: [] }]), { farms: 1, sites: 0, nodes: 0, sampleNodes: 0 });
  assert.deepEqual(farmSummary([]), { farms: 0, sites: 0, nodes: 0, sampleNodes: 0 });
});
test("summary preserves actual site associations and sample provenance", () => {
  const farms = [{ sites: [{ nodes: [{ node_id: "NODE_01", is_demo: 1, source: "synthetic_2025_two_nodes" }] }, { nodes: [{ node_id: "NODE_02", is_demo: 1, source: "synthetic_2025_two_nodes" }] }] }, { sites: [{ nodes: [{ node_id: "TEST_UNOBSERVED", is_demo: 0, source: "c1_not_ingested" }] }] }];
  assert.deepEqual(farmSummary(farms), { farms: 2, sites: 3, nodes: 3, sampleNodes: 2 });
});
