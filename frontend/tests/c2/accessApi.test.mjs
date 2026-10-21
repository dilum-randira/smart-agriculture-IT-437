import test, { afterEach } from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { accessApi, selectionQuery } from "../../src/services/c2/accessApi.js";

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

test("login uses credentialed cookies and CSRF stays in memory for later mutations", async () => {
  const nonce = randomUUID(), password = randomUUID();
  globalThis.fetch = async (url, options) => {
    assert.match(url, /\/api\/c2\/access\/login$/); assert.equal(options.credentials, "include");
    assert.equal(JSON.parse(options.body).password, password);
    return json({ user: { role: "researcher" }, csrf_token: nonce });
  };
  await accessApi("/login", { method: "POST", body: { username: "temporary_test_user", password } });
  globalThis.fetch = async (_url, options) => {
    assert.equal(new Headers(options.headers).get("X-CSRF-Token"), nonce); assert.equal(options.credentials, "include");
    assert.equal("Authorization" in options.headers, false); return json({ status: "saved" });
  };
  await accessApi("/farms", { method: "POST", body: { farm_name: "Test metadata only" } });
});
test("refresh restores server CSRF token and GET requests do not mutate state", async () => {
  const nonce = randomUUID();
  globalThis.fetch = async (_url, options) => { assert.equal(options.method, "GET"); assert.equal(options.body, undefined); return json({ user: { role: "viewer" }, csrf_token: nonce }); };
  await accessApi("/me");
  globalThis.fetch = async (_url, options) => { assert.equal(new Headers(options.headers).get("X-CSRF-Token"), nonce); return json({ status: "signed_out" }); };
  await accessApi("/logout", { method: "POST" });
  globalThis.fetch = async (_url, options) => { assert.equal(options.headers["X-CSRF-Token"], undefined); return json({}); };
  await accessApi("/login", { method: "POST", body: {} });
});
test("farm site and node are transmitted explicitly without fallback", () => {
  const query = selectionQuery("site_a", "NODE_02");
  assert.equal(new URLSearchParams(query).get("site_id"), "site_a");
  assert.equal(new URLSearchParams(query).get("node_id"), "NODE_02");
});
test("protected-route denials are surfaced rather than converted into public forecasts", async () => {
  let count = 0;
  globalThis.fetch = async () => { count++; return json({ detail: "Farm not found" }, 404); };
  await assert.rejects(accessApi("/farms/private/history"), /Farm not found/);
  assert.equal(count, 1);
  globalThis.fetch = async () => json({ detail: "Forbidden" }, 403);
  await assert.rejects(accessApi("/users"), /Forbidden/);
});
test("authentication and malformed validation errors do not expose posted credentials", async () => {
  globalThis.fetch = async () => json({ detail: "Internal private data" }, 401);
  await assert.rejects(accessApi("/me"), /Sign in required/);
  globalThis.fetch = async () => json({ detail: [{ input: "private posted password" }] }, 422);
  await assert.rejects(accessApi("/login", { method: "POST", body: {} }), (error) => !/private posted/.test(error.message));
});
test("network failures and explicit cancellation remain distinguishable", async () => {
  globalThis.fetch = async () => { throw new TypeError("Failed fetch"); };
  await assert.rejects(accessApi("/me"), /Local access service unavailable/);
  const controller = new AbortController(); controller.abort();
  await assert.rejects(accessApi("/me", { signal: controller.signal }), { name: "AbortError" });
});
test("a stale session refresh cannot replace CSRF state after a newer login", async () => {
  let release;
  const newer = randomUUID(), stale = randomUUID();
  globalThis.fetch = () => new Promise((resolve) => { release = resolve; });
  const refreshing = accessApi("/me");
  globalThis.fetch = async () => json({ user: { role: "researcher" }, csrf_token: newer });
  await accessApi("/login", { method: "POST", body: { username: "test_only_user", password: randomUUID() } });
  release(json({ user: { role: "viewer" }, csrf_token: stale }));
  await refreshing;
  globalThis.fetch = async (_url, options) => {
    assert.equal(new Headers(options.headers).get("X-CSRF-Token"), newer);
    return json({ status: "saved" });
  };
  await accessApi("/farms", { method: "POST", body: {} });
});

test("registration sends credentials without accepting client-selected privileges", async () => {
  const password = randomUUID();
  globalThis.fetch = async (url, options) => {
    assert.match(url, /\/access\/register$/);
    assert.equal(options.credentials, "include");
    assert.deepEqual(JSON.parse(options.body), { username: "test_only_farmer", password });
    return json({ status: "created", role: "viewer" }, 201);
  };
  assert.equal((await accessApi("/register", { method: "POST", body: { username: "test_only_farmer", password } })).role, "viewer");
});
