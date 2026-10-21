import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { build } from "esbuild";
import { mkdir, readFile, unlink } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

// Server rendering checks markup/data contracts; this is explicitly NOT a browser/WebGL test.
// Use the existing Vite/esbuild dependency to bundle JSX; no new test package is installed.
const temporary = resolve(`node_modules/.cache/c2-render-${process.pid}.mjs`);
await mkdir(resolve("node_modules/.cache"), { recursive: true });
const originalConsoleError = console.error;
const renderErrors = [];
console.error = (...args) => renderErrors.push(args.map(String).join(" "));
try {
  await build({ stdin: { contents: `export {default as Page} from './src/pages/c2/MicroclimateForecasting.jsx';
    export {default as Chart} from './src/components/c2/microclimate/ForecastChart.jsx';
    export {default as DashboardView} from './src/components/c2/microclimate/MicroclimateDashboardView.jsx';
    export {default as Atmosphere} from './src/components/c2/microclimate/ForecastAtmosphere.jsx';
    export {EnvironmentView} from './src/components/c2/microclimate/EnvironmentContext.jsx';
    export {default as ComparisonResults} from './src/components/c2/microclimate/ComparisonResults.jsx';
    export {default as ForecastDays} from './src/components/c2/microclimate/ForecastDays.jsx';
    export {groupForecastDays} from './src/services/c2/forecastDays.js';
    export {StaticFarm} from './src/components/c2/microclimate/FarmPanel.jsx';
    export {default as AccessPanel,LocationPlot} from './src/components/c2/microclimate/FarmAccess.jsx';
    export {default as AdminPage} from './src/pages/c2/FarmManagement.jsx';
    export {AuthContext} from './src/auth/AuthProvider.jsx';
    export {default as LoginPage} from './src/pages/Login.jsx';
    export {default as RegisterPage} from './src/pages/Register.jsx';
    export {default as FarmWorkspace} from './src/pages/c2/FarmWorkspace.jsx';
    export {default as Navbar} from './src/components/Navbar.jsx';
    export {default as YieldPage} from './src/pages/c2/YieldPrediction.jsx';
    export {default as AccessDenied} from './src/pages/AccessDenied.jsx';
    export {historicalSeries,VARIABLES} from './src/services/c2/microclimateApi.js';`, resolveDir: process.cwd() },
    bundle: true, packages: "external", platform: "node", format: "esm", jsx: "automatic", outfile: temporary,
    loader: { ".webp": "dataurl", ".css": "empty", ".csv": "text" } });
  const { Page, Chart, DashboardView, Atmosphere, EnvironmentView, ComparisonResults, ForecastDays, groupForecastDays, StaticFarm, AccessPanel, LocationPlot, AdminPage, AuthContext, LoginPage, RegisterPage, FarmWorkspace, Navbar, YieldPage, AccessDenied, historicalSeries, VARIABLES } = await import(pathToFileURL(temporary).href);
  const identity = { id: "test_only_id", username: "test_only_admin", role: "admin" };
  const render = (component, user = identity) => renderToStaticMarkup(createElement(MemoryRouter, null, createElement(AuthContext.Provider, { value: { user, status: "ready", error: "" } }, component)));
  const page = render(createElement(Page));
  for (const value of ["Microclimate", "Synthetic Data — Prototype Evaluation Only", "Not validated with real Sri Lankan", "Run forecast", "NODE_01", "NODE_02", "Close environment view"]) assert.ok(page.includes(value), value);
  assert.ok(page.includes("Use static view"), "The interactive scene is available in the supporting header panel");
  assert.ok(!page.includes("Mean forecast ·"), "No predictions are fabricated before a request");
  const base = new URL("../../../backend/experiments/c2/microclimate/api_integration_v1/", import.meta.url);
  const request = JSON.parse(await readFile(new URL("demo_request_NODE_01.json", base), "utf8"));
  const response = JSON.parse(await readFile(new URL("example_forecast_response.json", base), "utf8"));
  const fixtureSite = { site_id: "test_site", site_name: "Synthetic site NODE_01", nodes: [{ node_id: "NODE_01" }] };
  const fixtureFarm = { farm_id: "test_farm", farm_name: "Original synthetic record", is_demo: 1, sites: [fixtureSite], district: "Not verified", timezone: "Asia/Colombo", crop_type: "Capsicum chinense", provenance: "synthetic_2025_two_nodes" };
  const calls = [];
  const viewProps = { access: { user: identity, farm: fixtureFarm, site: fixtureSite, farms: [fixtureFarm], mode: "farm", selection: { farmId: "test_farm", siteId: "test_site", nodeId: "NODE_01" }, allowedNodes: ["NODE_01"] }, node: "NODE_01", model: response.model, horizon: 72, saved: [{ forecast_id: "fixture_saved", response, model: response.model }], demo: { request }, result: response, comparison: null, busy: "", loadingHistory: false, error: "", ready: true, history: historicalSeries(request.observations), predictions: response.predictions, days: groupForecastDays(response.predictions, 72), selectedDay: null, selectedGroup: null, visiblePredictions: response.predictions.slice(0, 72), onModel: (value) => calls.push(["model", value]), onHorizon: (value) => calls.push(["horizon", value]), onNode: () => {}, onPredict: (value) => calls.push(["predict", value]), onRetry: () => {}, onSaved: (value) => calls.push(["saved", value]), onDay: () => {} };
  const assignmentFailure = render(createElement(AccessPanel, { access: { ...viewProps.access, farms: [], farm: null, site: null, accessError: "Backend unavailable", accessBusy: false } }));
  assert.ok(assignmentFailure.includes("Farm assignments could not be loaded"));
  assert.ok(!assignmentFailure.includes("No farms assigned to this account"), "A failed request is not evidence of missing membership");
  assert.ok(assignmentFailure.includes("Refresh farm assignments"));
  const noMembership = render(createElement(AccessPanel, { access: { ...viewProps.access, farms: [], farm: null, site: null, accessError: "", accessBusy: false } }));
  assert.ok(noMembership.includes("Ask an Admin"));
  const loadedView = render(createElement(DashboardView, viewProps));
  for (const value of ["Farm &amp; observation node", "Forecast settings", "Sample Data — Not Live Sensor Readings", "Your next 72 hours", "FORECAST START", "FORECAST END", "All Days", "Data context &amp; model provenance"]) assert.ok(loadedView.includes(value), value);
  assert.ok(!loadedView.includes("NaN")); assert.ok(!loadedView.includes("undefined"));
  const order = ["environment-context", "forecast-workspace", "forecast-insights", "model-comparison"].map((id) => loadedView.indexOf(`id="${id}"`));
  assert.ok(order.every((index, i) => index >= 0 && (!i || index > order[i - 1])), "Supporting 3D does not interrupt the control/chart workspace");
  assert.ok(loadedView.includes("ACTIVE MODEL")); assert.ok(loadedView.includes("OBSERVATION NODE"));
  for (const path of ["icons/metrics/air-temperature.svg", "icons/metrics/relative-humidity.svg", "icons/metrics/soil-moisture.svg", "illustrations/farm/isometric-open-field.svg"]) assert.ok(loadedView.includes(`/assets/nai-miris/${path}`), path);
  for (const unsupported of ["sunny.svg", "rainy.svg", "cloudy.svg", "thunderstorm.svg"]) assert.ok(!loadedView.includes(unsupported));
  let environmentToggles = 0;
  const environmentProps = { access: viewProps.access, node: "NODE_01", onNode: () => {}, predictions: response.predictions, horizon: 72, expanded: false, onToggle: () => environmentToggles++ };
  const closedEnvironment = render(createElement(EnvironmentView, environmentProps));
  assert.ok(closedEnvironment.includes('aria-expanded="false"')); assert.ok(closedEnvironment.includes('hidden=""'));
  assert.ok(!closedEnvironment.includes("Use static view"));
  const openedEnvironment = render(createElement(EnvironmentView, { ...environmentProps, expanded: true }));
  assert.ok(openedEnvironment.includes('aria-expanded="true"')); assert.ok(!openedEnvironment.includes('hidden=""'));
  assert.ok(openedEnvironment.includes("Use static view")); assert.ok(openedEnvironment.includes("not an installed IoT field"));
  assert.ok(openedEnvironment.includes("NODE_01"));
  const selectedGroup = viewProps.days[0];
  const selectedView = render(createElement(DashboardView, { ...viewProps, selectedDay: selectedGroup.key, selectedGroup, visiblePredictions: selectedGroup.rows, comparison: [{ ...response, model: "lstm" }, { ...response, model: "gru" }, response] }));
  assert.ok(selectedView.includes(selectedGroup.weekday));
  assert.ok(selectedView.includes("Whole 72-hour horizon, independent of day selection"));
  const walk = (node) => Array.isArray(node) ? node.flatMap(walk) : node && typeof node === "object" && node.props ? [node, ...walk(node.props.children)] : [];
  walk(EnvironmentView(environmentProps)).find((node) => node.type === "button").props.onClick();
  assert.equal(environmentToggles, 1);
  const elements = walk(DashboardView(viewProps));
  elements.find((node) => node.props.id === "mc-model").props.onChange({ target: { value: "gru" } });
  elements.find((node) => node.props.id === "mc-saved").props.onChange({ target: { value: "fixture_saved" } });
  elements.find((node) => node.type === "button" && node.props.className === "mc-run-button").props.onClick();
  elements.find((node) => node.type === "button" && node.props.className === "mc-secondary-button").props.onClick();
  const horizonButtons = walk(elements.find((node) => node.props.className === "mc-horizon-switch").props.children).filter((node) => node.type === "button");
  horizonButtons.forEach((button) => button.props.onClick());
  assert.deepEqual(calls, [["model", "gru"], ["saved", "fixture_saved"], ["predict", false], ["predict", true], ["horizon", 24], ["horizon", 72], ["horizon", 168]]);
  const equalComparison = render(createElement(ComparisonResults, { comparison: ["lstm", "gru", "attention_bilstm"].map((model) => ({ ...response, model })), activeModel: "gru", horizon: 72, node: "NODE_01" }));
  assert.ok(equalComparison.includes("0.00")); assert.ok(equalComparison.includes("Equal model means; not an accuracy score"));
  assert.equal((equalComparison.match(/data-active="true"/g) || []).length, 1);
  assert.ok(equalComparison.includes("Selected model")); assert.ok(!equalComparison.includes("NaN"));
  const emptyAtmosphere = render(createElement(Atmosphere, { predictions: [], horizon: 24 }));
  assert.ok(!emptyAtmosphere.includes("°C</small></strong>27"));
  assert.ok(emptyAtmosphere.includes("Select your node and run a forecast"));
  let charts = 0;
  for (const variable of VARIABLES) for (const horizon of [24, 72, 168]) {
    const html = renderToStaticMarkup(createElement(Chart, { variable, horizon, history: historicalSeries(request.observations), predictions: response.predictions, origin: response.forecast_origin }));
    for (const value of ["Forecast origin", "Inspect hourly value", variable.unit, `${horizon}-hour forecast`, "Causally filled input"]) assert.ok(html.includes(value), value);
    charts++;
  }
  let dailyCharts = 0;
  for (const horizon of [24, 72, 168]) {
    const days = groupForecastDays(response.predictions, horizon);
    let selection = null;
    const props = { days, horizon, selectedDay: null, onSelect: (key) => { selection = key; } };
    const tabs = ForecastDays(props).props.children[1].props.children;
    const buttons = [tabs[0], ...tabs[1]];
    buttons[1].props.onClick(); assert.equal(selection, days[0].key);
    buttons[0].props.onClick(); assert.equal(selection, null);
    const all = renderToStaticMarkup(createElement(ForecastDays, props));
    assert.ok(all.includes("All Days")); assert.ok(all.includes("Asia/Colombo"));
    assert.equal((all.match(/aria-pressed="true"/g) || []).length, 1);
    for (const day of days) {
      const dayTabs = renderToStaticMarkup(createElement(ForecastDays, { ...props, selectedDay: day.key }));
      assert.ok(dayTabs.includes(day.weekday)); assert.ok(dayTabs.includes(day.date));
      const temperatureValues = day.rows.map((row) => row.air_temperature_c);
      const meanHumidity = day.rows.reduce((sum, row) => sum + row.relative_humidity_pct, 0) / day.count;
      const meanSoil = day.rows.reduce((sum, row) => sum + row.soil_moisture_avg_index, 0) / day.count;
      assert.ok(dayTabs.includes(`${Math.min(...temperatureValues).toFixed(1)}–${Math.max(...temperatureValues).toFixed(1)} °C`));
      assert.ok(dayTabs.includes(`${meanHumidity.toFixed(1)}% RH`));
      assert.ok(dayTabs.includes(`${meanSoil.toFixed(1)} INDEX`));
      assert.ok(dayTabs.includes(`dateTime="${day.start}"`)); assert.ok(dayTabs.includes(`dateTime="${day.end}"`));
      assert.equal((dayTabs.match(/aria-pressed="true"/g) || []).length, 1);
      for (const variable of VARIABLES) {
        const html = renderToStaticMarkup(createElement(Chart, { variable, horizon, selectedDay: day.key, history: historicalSeries(request.observations), predictions: response.predictions, origin: response.forecast_origin }));
        assert.ok(html.includes(`${day.count} hourly forecasts on ${day.key}`));
        assert.ok(html.includes("Selected calendar day only")); assert.ok(html.includes(variable.unit));
        assert.ok(!html.includes("History view")); assert.ok(!html.includes("NaN")); assert.ok(!html.includes("undefined"));
        dailyCharts++;
      }
    }
  }
  // A real API row on its own remains drawable and inspectable, without invented values.
  const single = response.predictions.slice(0, 1), singleDay = groupForecastDays(single, 24)[0];
  for (const variable of VARIABLES) {
    const html = renderToStaticMarkup(createElement(Chart, { variable, horizon: 24, selectedDay: singleDay.key, history: [], predictions: single, origin: response.forecast_origin }));
    assert.ok(html.includes('max="0"')); assert.ok(!html.includes("NaN"));
    assert.ok(html.includes(single[0][variable.key].toFixed(2)));
  }
  const fallback = renderToStaticMarkup(createElement(StaticFarm));
  assert.ok(fallback.includes("Static conceptual farm diagram")); assert.ok(fallback.includes("NODE_02"));
  assert.ok(fallback.includes("/assets/nai-miris/illustrations/farm/isometric-open-field.svg"));
  for (const role of ["admin", "researcher", "viewer"]) {
    const access = { user: { username: "test_only_user", role }, mode: "farm", selection: {}, farms: [] };
    const html = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(AccessPanel, { access })));
    assert.equal(html.includes("Manage users, farms &amp; nodes"), role === "admin");
    assert.ok(html.includes("Your assignments determine which sites"));
  }
  assert.equal(renderToStaticMarkup(createElement(LocationPlot, { latitude: null, longitude: null })), "");
  assert.ok(renderToStaticMarkup(createElement(LocationPlot, { latitude: 0, longitude: 0 })).includes("verification pending"));
  assert.ok(render(createElement(AdminPage), { ...identity, role: "viewer" }).includes("Administrator access is required"));
  const login = render(createElement(LoginPage), null);
  for (const value of ['name="username"', 'type="password"', 'autoComplete="current-password"', "Show", "Create a Farmer account"]) assert.ok(login.includes(value), value);
  assert.ok(!login.includes('value="test_only'));
  assert.ok(login.includes("/assets/nai-miris/branding/logo-horizontal-light.svg"));
  const registration = render(createElement(RegisterPage), null);
  for (const value of ['name="username"', 'autoComplete="new-password"', 'minLength="12"', 'Create Farmer account', 'name="confirm"']) assert.ok(registration.includes(value), value);
  assert.ok(!registration.includes('name="role"'));
  for (const view of ["overview", "farms", "sensors", "monitoring", "account"]) {
    const html = render(createElement(FarmWorkspace, { view }), { ...identity, role: "viewer" });
    assert.ok(html.includes("Smart Agriculture"));
    if (view === "farms") assert.ok(html.includes("Create my farm"));
    if (view === "account") assert.ok(html.includes("Roles cannot be changed"));
  }
  const navbar = render(createElement(Navbar, { navigation: [{ path: "/farms", shortName: "My Farms" }] }), { ...identity, role: "viewer" });
  for (const value of ['aria-controls="primary-navigation"', 'aria-expanded="false"', 'My Farms', 'Farmer', 'Logout']) assert.ok(navbar.includes(value), value);
  const { navigationForRole } = await import("../../src/services/navigation.js");
  for (const role of ["admin", "researcher", "viewer"]) {
    const html = render(createElement(Navbar, { navigation: navigationForRole(role) }), { ...identity, role });
    assert.equal(html.includes('href="/predictions/manage"'), role === "admin");
    assert.ok(html.includes("Application sidebar")); assert.ok(html.includes("app-account-dropdown"));
    assert.ok(html.includes("/assets/nai-miris/icons/navigation/overview.svg"));
    assert.ok(html.includes(`/assets/nai-miris/branding/avatar-${role === "viewer" ? "farmer" : role}.svg`));
  }
  const yieldPage = render(createElement(YieldPage));
  for (const value of ["yield-estimator", "XGBoost", "Random Forest", "SVR", "g/plant", "illustrations/crops/nai-miris-pepper-hero.svg"]) assert.ok(yieldPage.includes(value), value);
  assert.ok(render(createElement(AccessDenied)).includes("This section is not available to your role"));
  assert.deepEqual(renderErrors, [], "React server rendering must not emit errors or accessibility-title warnings");
  console.log(JSON.stringify({ page_markup: "passed", local_asset_markup: "passed", role_sidebar_states: 3, yield_page: "passed", loaded_dashboard_and_daily_view: "passed", optional_environment_states: 2, environment_order_and_toggle: "passed", comparison_markers: "passed", configuration_callbacks: 7, chart_renders: charts, day_chart_renders: dailyCharts, day_button_callbacks: "passed", single_hour_charts: 3, static_fallback_markup: "passed", role_visibility_states: 3, location_and_admin_markup: "passed", registration_and_farmer_pages: 6, mobile_menu_markup: "passed", browser_or_webgl_verified: false }));
} finally { console.error = originalConsoleError; await unlink(temporary).catch(() => {}); }
