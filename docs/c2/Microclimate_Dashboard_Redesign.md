# Microclimate dashboard redesign

The latest local-asset integration and lighter, reference-inspired sidebar/forecast workspace are documented in [Asset Integration & UI Refinement](Asset_Integration_UI_Refinement.md). That guide supersedes the earlier hero/control-layout descriptions below while retaining the same forecasting and honesty constraints.

## Current revision: forecast-first, optional environment context

This revision replaces the former large 3D centerpiece/control rail described below. The order is now **hero → horizontal control console → forecast KPIs and charts → optional environment context → model comparison → provenance**.

- **3D is secondary:** collapsed by default after the charts, with only a small decorative static thumbnail. Expand to mount a compact side-aligned scene beside site/node context; close to unmount the renderer and release its resources through the existing cleanup. The scene uses its existing transparent canvas, soft edge blending and restrained temperature/humidity atmosphere accents. No hard outer card border or full-width central scene. Rotate/zoom, node authorization, static fallback and reduced-motion behavior remain available.
- **Palette:** neutral gray/slate base and surfaces; dark navy/petrol hero; blue horizon/day selections and humidity signals; amber temperature; green soil/vegetation and brand actions; muted violet model metadata. KPI backgrounds and icon/marker colors now distinguish the three target variables rather than repeating pale green.
- **Hero:** current selected model, horizon and node are explicit. The environmental highlight still uses actual horizon temperature/humidity means and never infers precipitation, clouds or sunlight.
- **Controls/charts:** a three-part horizontal console replaces the old rail/scene split; it stacks on small screens. The forecast-origin marker and forecast region have stronger contrast and an explicit hourly forecast annotation. Actual day/date selection and original values are unchanged.
- **Comparison:** highlights the selected model and shows calculated spreads and relative positions among horizon means. These are output differences, not accuracy rankings or recommendations; equal means are handled without division by zero.

Files changed in this revision: `frontend/src/components/c2/microclimate/MicroclimateDashboardView.jsx`, `ForecastChart.jsx`, new `EnvironmentContext.jsx`, new `ComparisonResults.jsx`, `frontend/src/styles/c2/microclimate.css`, `frontend/tests/c2/microclimateRender.mjs`, and this document. The shared navigation/profile from the previous revision is retained.

Executed verification: **51 frontend tests passed; render checks and build passed.** Render checks additionally verify the section order, both environment states and toggle callback, absence of the interactive scene when collapsed, all seven forecast configuration callbacks, selected-model highlighting and finite equal-model comparison markers. Existing nine horizon charts, 42 day charts, three single-hour charts, role/navigation and Yield tests pass. No new external assets, packages, model training or backend changes.

Browser/mobile/WebGL visual verification remains manual: no browser surface was available, and the earlier headless-browser launch was rejected by automatic approval review. No alternative launch was attempted. Suggested manual checks include expanded/collapsed environment at 360/768/1024/1440px, no document overflow, chart and selector readability, keyboard toggle/focus, scene controls and no renderer activity after closing.

---

## Earlier redesign foundation

The `/predictions/microclimate` page now uses a 1600px workspace with a forest-green hero, restrained sky/earth accents, larger typography and a clear operational sequence: configure → inspect spatial context → explore hourly/daily outputs → compare models → inspect evidence.

## Intentional changes

- Replaced the narrow hero/photo split with one integrated environmental header. The existing licensed Capsicum image remains a botanical reference, with attribution in Data Context.
- Consolidated farm/site/node, model, horizon, run and saved-forecast controls in one rail. Technical location identifiers and provenance are available in expandable details. Friendly labels preserve the actual selected IDs and original metadata.
- Expanded the existing lazy-loaded 3D farm into a spatial overview module with focused-node status, clear interaction guidance and its original static/WebGL fallback. No scene geometry, orbit logic or model behavior changed.
- Moved calendar-day navigation ahead of the KPI cards so the chosen day visibly controls the summaries and charts below. All Days, partial days and Asia/Colombo timestamps retain their existing behavior. Model comparison explicitly uses the whole selected horizon.
- Larger KPI values, actual-value sparklines, clearer chart legends/axes, saved history states and comparison tables. Selection/loading without a farm is treated as an empty state rather than a forecast error.
- Shared header retains all routes and role filtering, with a proper username/role/avatar/account area and logout. Navigation and layout styles cover desktop, tablet and mobile. Motion respects reduced-motion preferences; chart/table/day-strip overflow stays inside the relevant module.
- One prominent but restrained **Sample Data — Not Live Sensor Readings** notice remains visible. Full synthetic evaluation labels, history timestamps, model artifact IDs, filling counts and limitations remain in Data Context. No observed rainfall, sunlight, cloud cover or live telemetry is implied.

## Environmental visuals

The hero reads actual cumulative forecast temperature and humidity means. Humidity means at least 80% use a cool humidity accent; otherwise temperature means at least 32°C use a warm accent; other values use the neutral cultivation palette. These are **presentation choices only**, not meteorological classifications, validated crop thresholds, warnings or recommendations. Missing forecasts show no numeric values. Rain/cloud predictions cannot be inferred from these three trained features and are not fabricated.

Sparklines contain one display point per supplied hourly value, on a relative scale. They do not smooth, interpolate or alter model output values. No datasets, checkpoints, scalers, APIs, memberships or backend permissions were changed.

## Files

- Modified: `frontend/src/pages/c2/MicroclimateForecasting.jsx` (state and API container), `frontend/src/components/c2/microclimate/FarmAccess.jsx`, `FarmPanel.jsx`, `frontend/src/styles/c2/microclimate.css`, `frontend/src/components/Navbar.jsx`, `frontend/tests/c2/microclimateRender.mjs`.
- Added: `frontend/src/components/c2/microclimate/MicroclimateDashboardView.jsx`, `ForecastAtmosphere.jsx`, `frontend/src/services/c2/forecastVisuals.js`, `frontend/src/styles/navigation.css`, `frontend/tests/c2/forecastVisuals.test.mjs`, this document.
- Existing ForecastChart, ForecastDays, timezone helpers, API clients, auth provider/policy and Three.js scene implementation are reused.

## Verification

From `frontend/`:

```powershell
npm run test:c2
npm run test:microclimate:render
npm run build
```

Executed: **51 frontend tests passed, zero failures**; render verification passed for loaded/empty dashboards, selected-day and comparison views, seven configuration callbacks, nine full-horizon charts, 42 daily charts, three single-hour charts, role visibility, login/registration/farm pages and navigation. Build passed. Render checks explicitly do not establish browser/WebGL behavior.

No browser surface was available. Automatic approval review rejected launching installed Chrome headlessly with “blocked by policy.” Actual screenshots, mobile geometry, hover/touch behavior and WebGL interaction therefore remain manual checks. Recommended widths: 360, 768, 1024 and 1440px. Confirm no document-level overflow, reachable profile/menu/logout, all three models/horizons, both authorized site/node selections, saved results and the synthetic data disclosure.

No assets or packages installed, models retrained, commits, pushes or deployments performed. The previously attributed botanical image is reused; the now-unused irrigation/station images remain untouched in the repository and are no longer bundled by this page.
