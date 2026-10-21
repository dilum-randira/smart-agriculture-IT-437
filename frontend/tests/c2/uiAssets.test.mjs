import test from "node:test";
import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { resolveConfig } from "vite";
import { ASSET_BASE, ASSET_FILES, assetUrl, avatarAsset, NAV_ASSET_BY_PATH } from "../../src/services/uiAssets.js";
import { navigationForRole } from "../../src/services/navigation.js";
import { canAccess } from "../../src/auth/policy.js";

const pack = new URL("../../src/public/assets/nai-miris/", import.meta.url);
const manifest = JSON.parse(await readFile(new URL("docs/asset-manifest.json", pack), "utf8"));

test("resolved Vite public directory is src/public; the installed pack needs no relocation", async () => {
  const config = await resolveConfig({}, "serve");
  assert.equal(resolve(config.root), resolve("src"));
  assert.equal(resolve(config.publicDir), resolve("src/public"));
});
test("every shared asset path exists in the original manifest and filesystem", async () => {
  const paths = new Set(manifest.assets.map((asset) => asset.path));
  for (const [key, path] of Object.entries(ASSET_FILES)) {
    assert.ok(paths.has(path), key);
    assert.ok((await stat(new URL(path, pack))).size > 0, key);
    assert.equal(assetUrl(key), `${ASSET_BASE}/${path}`);
    assert.ok(path.endsWith(".svg"), "UI integrations prefer SVG rather than large raster exports");
  }
  assert.throws(() => assetUrl("https://external.example"), /Unknown local asset/);
  assert.throws(() => assetUrl("../missing.svg"), /Unknown local asset/);
});
test("all 264 original manifest assets remain present", async () => {
  assert.equal(manifest.assets.length, 264);
  await Promise.all(manifest.assets.map(async ({ path }) => assert.ok((await stat(new URL(path, pack))).size > 0, path)));
});
test("all authorized sidebar routes use existing policy and pack icons", () => {
  for (const role of ["admin", "researcher", "viewer"]) {
    const items = navigationForRole(role);
    for (const item of items) { assert.ok(canAccess(role, item.path)); assert.ok(ASSET_FILES[NAV_ASSET_BY_PATH[item.path]]); }
    assert.equal(items.some((item) => item.path === "/predictions/manage"), role === "admin");
    for (const path of ["/predictions", "/predictions/microclimate", "/farms", "/sensors", "/account"]) assert.ok(items.some((item) => item.path === path));
  }
  assert.deepEqual(navigationForRole("unknown"), []);
});
test("role avatars preserve internal viewer-to-Farmer mapping", () => {
  assert.equal(avatarAsset("viewer"), "avatarFarmer");
  assert.equal(avatarAsset("researcher"), "avatarResearcher");
  assert.equal(avatarAsset("admin"), "avatarAdmin");
});
test("only unknown weather artwork is exposed; unsupported conditions cannot be selected", () => {
  assert.deepEqual(Object.keys(ASSET_FILES).filter((key) => key.startsWith("weather")), ["weatherUnknown"]);
  for (const condition of ["sunny", "rainy", "cloudy", "mist", "thunderstorm", "windy"]) assert.ok(!Object.values(ASSET_FILES).includes(`weather/icons/${condition}.svg`));
});
