# Local asset integration and reference-inspired workspace

Implemented on `feature/c2-predictive-intelligence`. This is a frontend integration; no backend, account database, training data, checkpoint, scaler or prediction algorithm was changed.

## Public directory verified before editing

`frontend/vite.config.js` sets Vite's **root to `frontend/src`**. Vite's resolved default public directory is therefore **`frontend/src/public`**, not `frontend/public`. This was confirmed with `vite.resolveConfig` and an automated test. The supplied pack was already correct at:

```text
frontend/src/public/assets/nai-miris/
```

The README, `docs/asset-manifest.json`, `docs/tokens.css`, actual SVG sources and PNG previews were inspected. All **264 manifest assets** exist. The pack has **268 files** including supporting documentation/preview files. Source hashes show all 268 are unchanged; there was no relocation or second source copy. Vite's production public-asset copy was checked byte-for-byte against the original pack.

Example live URL: `http://127.0.0.1:5173/assets/nai-miris/icons/navigation/overview.svg`.

## Working-feature inventory preserved

Before editing, the existing implementation contained login/register, shared auth/route guards, SQLite sessions and CSRF, three roles, farm/site/node membership, NODE_01/NODE_02, LSTM/GRU/Attention BiLSTM, 24/72/168-hour views, calendar-day selection, all three historical/forecast charts and inspectors, saved forecasts, comparison, optional interactive Three.js, static fallback, Yield form and RF/SVR/XGBoost research comparison material. These remain reachable; no feature was exchanged for a decorative image.

## Reference interpretation and design

The supplied screenshot guided the **composition**, not its example data: desktop navigation rail, compact location/model controls on the left, a lighter illustrated environmental header, distinct metric cards and daily forecast cards. The original full-width hourly trajectories remain readable rather than becoming three tiny decorative charts. Smaller screens stack the controls and outputs, and use the mobile navigation drawer.

No reference-image farm coordinates, example readings, forecast dates, wind readings, weather conditions or previous-period deltas were copied. All numeric output comes from existing API responses. Calendar-day cards calculate temperature min/max, mean relative humidity and mean soil-moisture INDEX from only that calendar day's returned rows, within the selected horizon. Dates remain in Asia/Colombo, including partial days and All Days.

The shell uses a neutral white/slate palette with green brand actions, amber temperature, blue humidity and green soil signals. Native image dimensions reserve layout space. The supplied horizontal logo's excess transparent right canvas is cropped only through CSS; its original SVG is unchanged.

## Assets actually used

All references are local URLs under `/assets/nai-miris/`. `services/uiAssets.js` provides explicit, manifest-verified paths; `components/ui/Asset.jsx` supplies accessible image/icon/brand wrappers.

- **Branding:** `branding/logo-horizontal-light.svg`, `branding/avatar-admin.svg`, `branding/avatar-researcher.svg`, `branding/avatar-farmer.svg`, `branding/favicon.svg`.
- **Navigation:** `icons/navigation/overview.svg`, `my-farms.svg`, `monitoring.svg`, `microclimate.svg`, `yield-prediction.svg`, `sensor-nodes.svg`, `my-account.svg`, `admin.svg`, `logout.svg`, `login.svg`, `register.svg`, `analytics.svg`.
- **Metrics/crop:** `icons/metrics/air-temperature.svg`, `relative-humidity.svg`, `soil-moisture.svg`, and `icons/crops/plant.svg`.
- **Controls/feedback:** existing pack icons for menu, collapse, arrow-right, chevron-down, calendar, clock, compare, settings, refresh, eye/eye-off, location, chart-line, notification, available, error, info, sample-data, no-data and locked. Feedback reflects real application states; there is no invented notification service, unread count or device-online status.
- **Illustrations:** `illustrations/crops/nai-miris-pepper-hero.svg`, `illustrations/farm/isometric-open-field.svg`, and the `no-farms.svg`, `no-sensors.svg`, `no-forecast.svg` empty-state illustrations.
- **Surfaces/overlays:** `backgrounds/surface-neutral.svg`, `surface-dark-forest.svg` (shared earlier hero skin, overridden by the lighter reference layout), `overlays/3d-ground-blend.svg`, `edge-fade-light.svg`.
- **Unknown weather:** only `weather/icons/no-data.svg`, explicitly labelled as unavailable weather conditions. The asset registry does not expose sunny/rainy/cloudy/storm/wind conditions to this UI.

Registry entries are not all downloaded: only actual image/CSS references request assets. UI references prefer SVG; raster exports remain intact but are not used as chart or live-weather substitutes. No new asset library, external image host or package was added. Original botanical photos and the previous Yield SVG remain untouched but are no longer required by these pages.

## Shell and accessibility

- Desktop sidebar follows the **existing route-role policy** through `navigationForRole`; it does not create new authorization logic. Admin management appears only for Admin. Existing guards and backend permissions remain authoritative.
- The mobile drawer has an explicit open/close control, backdrop, Escape handling, focus containment/restoration, body-scroll restoration and closes on route or desktop-breakpoint changes.
- The account dropdown uses native disclosure semantics, role-specific generic avatars, current username/role, account link and the existing session-revoking logout. It dismisses on outside pointer interaction or Escape.
- Login/register retain the same forms, validation, password-manager attributes, password visibility controls, intended-destination handling and requests. The changes are branding/art/icon presentation.
- Farm and sensor empty states remain honest about unavailable data; registration does not silently assign sample farms or sensors.

## Interactive environment retained

The original `FarmScene.jsx` remains unchanged: node permissions, orbit, rotation, zoom/camera controls, responsive resize and resource cleanup are preserved. It is mounted only when the optional environment view is expanded. The supplied ground/edge overlays sit behind or around the canvas; decorative layers have `pointer-events:none`. The supplied isometric illustration is only the preview/static fallback, never a replacement for the interactive renderer.

No illustration is interpreted as a measurement, genuine physical device layout, geographic position or weather classification. Reduced-motion support and the existing WebGL-unavailable fallback remain.

## Modified and added files

| Area | Files |
|---|---|
| Shell | `frontend/src/App.jsx`, `components/Navbar.jsx`, `services/navigation.js` (new), `styles/navigation.css` |
| Shared assets | `frontend/src/components/ui/Asset.jsx` (new), `services/uiAssets.js` (new), `styles/assets.css` (new), `src/index.html` |
| Public auth | `frontend/src/pages/Login.jsx`, `Register.jsx` |
| Farm/account/admin | `frontend/src/pages/c2/FarmWorkspace.jsx`, `FarmManagement.jsx` |
| Yield presentation | `frontend/src/components/c2/YieldHero.jsx`, `YieldIcon.jsx` |
| Microclimate presentation | `frontend/src/components/c2/microclimate/ClimateIcon.jsx`, `ForecastAtmosphere.jsx`, `ForecastDays.jsx`, `FarmPanel.jsx`, `MicroclimateDashboardView.jsx`, `frontend/src/styles/c2/referenceWorkspace.css` (new) |
| Tests | `frontend/tests/c2/uiAssets.test.mjs` (new), `microclimateRender.mjs` |
| Documentation | This guide and the current-guide link in `Microclimate_Dashboard_Redesign.md` |

Paths abbreviated in a table cell share the stated frontend folder. Vite configuration, API clients/contracts, auth provider/route policy, Three.js renderer, ML implementation and asset-pack source files were not modified.

## Verification executed

From `frontend/`:

```powershell
npm run test:c2
npm run test:microclimate:render
npm run build
```

- **57 frontend tests passed, zero failures.** New tests cover actual Vite public resolution, all registry paths, the complete manifest, role-aware sidebar routes, role avatars and unsupported-weather exclusion.
- **Render checks passed:** loaded/empty dashboard, three role-sidebar states, branded login/register, five farm/account views, Admin visibility, Yield form/research panels, seven forecast-control callbacks, all nine variable/horizon chart combinations, 42 daily charts and three single-hour charts. Day-card displayed statistics are checked against actual saved API rows.
- **Production build passed.** Three.js remains in optional chunks. The render test harness now supports Vite-style raw CSV imports so the existing Yield research material can be verified without changing its data or implementation.
- **13 representative live asset URLs returned HTTP 200** with SVG/PNG MIME types and valid image content, including overview, branding/avatar, all three metrics, farm illustration, ground blend, neutral surface, unknown-weather icon, SVG/PNG favicon and PNG preview.
- All **268 original pack files** and **250 protected research/model/preprocessing/data/experiment files** matched their saved SHA-256 inventories. Production pack copying matched source bytes. `git diff --check` passed.
- Backend regression tests were not rerun because backend code did not change, as requested. No database reset, account edit, training, install, commit, push or deployment occurred.

## Feature-preservation evidence and remaining manual checks

| Feature | Evidence in this step |
|---|---|
| Login/session/CSRF/register/RBAC | Existing frontend API/policy tests; branded-page and role-sidebar renders; backend unchanged |
| Farm/site/node, NODE_01/NODE_02 | Explicit selection callbacks and actual prepared input contracts retained; no assignment tables changed |
| Three models, horizons, saved results, comparison | Existing transport/validation tests, seven configuration callbacks, actual saved-response chart renders |
| All historical/predicted trajectories and inspectors | Original chart implementation reused; nine horizon/42 day/three single-hour renders pass |
| Day summaries | Calculated from the returned day rows; tests check range/means and original-unit labels |
| Three.js interactions | Renderer source unchanged; expanded/collapsed/fallback renders and wrapper tests pass; actual pointer/WebGL behavior remains manual |
| Yield | Request/validation tests and full page render, including XGBoost/RF/SVR comparison material; original values preserved |

The existing served Yield API is tuned XGBoost; Random Forest/SVR remain the existing research comparison material, not newly claimed serving endpoints. No new model-serving capability is fabricated.

There is no available browser surface. Previous automatic approval review rejected a headless-browser launch, so no alternative launch was attempted. **Actual screenshots, drawer focus/scroll behavior, account dropdown interaction, login refresh/logout, node/model execution through the browser, chart hover/touch and WebGL camera controls remain manual checks.** Check 360/768/1024/1440px widths, document overflow, keyboard focus, all three models/horizons, both assigned nodes and Yield. Automated renders do not establish these browser outcomes.

Weather conditions remain unknown without a verified live/future source. NASA POWER history is not used as a weather forecast. Synthetic sample provenance and the uncalibrated soil-moisture INDEX label remain visible/available.
