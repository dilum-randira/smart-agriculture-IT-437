import test from "node:test";
import assert from "node:assert/strict";
import { canAccess, guardDecision, safeDestination } from "../../src/auth/policy.js";

test("all application destinations require a restored identity", () => {
  for (const path of ["/", "/monitoring", "/predictions", "/predictions/yield", "/predictions/microclimate", "/integration", "/irrigation", "/harvest", "/predictions/manage"]) {
    assert.equal(guardDecision({ status: "ready", user: null }, path), "login");
    assert.equal(guardDecision({ status: "loading", user: null }, path), "loading");
  }
});
test("navigation and route guard share conservative role rules", () => {
  for (const role of ["admin", "researcher"]) {
    for (const path of ["/", "/monitoring", "/predictions", "/predictions/microclimate", "/integration", "/irrigation", "/harvest"]) assert.ok(canAccess(role, path));
  }
  assert.ok(canAccess("admin", "/predictions/manage"));
  assert.equal(canAccess("researcher", "/predictions/manage"), false);
  for (const path of ["/integration", "/irrigation", "/harvest", "/predictions/manage"]) assert.equal(canAccess("viewer", path), false);
  for (const path of ["/", "/monitoring", "/predictions", "/predictions/yield", "/predictions/microclimate", "/access-denied", "/farms", "/sensors", "/account"]) assert.ok(canAccess("viewer", path));
});
test("authenticated unauthorized roles get access denied instead of a login loop", () => {
  for (const role of ["researcher", "viewer"]) assert.equal(guardDecision({ status: "ready", user: { role } }, "/predictions/manage"), "denied");
  assert.equal(guardDecision({ status: "ready", user: { role: "viewer" } }, "/access-denied"), "allow");
  assert.equal(guardDecision({ status: "error", user: null }, "/"), "error");
});
test("safe redirects preserve known internal destinations and reject open redirects", () => {
  for (const path of ["/predictions/microclimate?node=NODE_02#charts", "/predictions/manage", "/monitoring"]) assert.equal(safeDestination(path), path);
  for (const unsafe of [null, "", "https://untrusted.example", "//untrusted.example", "/\\untrusted.example", "/%2f%2funtrusted.example", "/login", "/unknown", "/predictions\n", "javascript:alert(1)", "/%00", "/%zz"]) assert.equal(safeDestination(unsafe), "/");
});
test("expired or revoked identities return to login and unknown roles do not gain access", () => {
  assert.equal(guardDecision({ status: "ready", user: null }, "/predictions/manage"), "login");
  assert.equal(guardDecision({ status: "ready", user: { role: "unknown" } }, "/"), "denied");
});
test("case, trailing slashes and encoded paths cannot bypass route permissions", () => {
  for (const path of ["/INTEGRATION", "/integration/", "/%69ntegration", "/predictions/MANAGE/"]) assert.equal(canAccess("viewer", path), false);
  assert.equal(canAccess("researcher", "/PREDICTIONS/MANAGE/"), false);
  assert.equal(safeDestination("/PREDICTIONS/MICROCLIMATE/"), "/predictions/microclimate");
});
