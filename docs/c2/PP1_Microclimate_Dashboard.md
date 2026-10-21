# Microclimate Forecasting dashboard

**Synthetic Data — Prototype Evaluation Only**

Implemented October 21, 2026 on `feature/c2-predictive-intelligence`. The existing
React/Vite frontend previously contained only Yield Prediction. This adds the
Microclimate workspace without replacing Yield or the shared application.

## Run locally

Terminal 1, from `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, from `frontend/`:

```powershell
npm run dev
```

Open **http://localhost:5173/predictions/microclimate**. Yield Prediction remains
at `/predictions`. The Microclimate link is available in the existing desktop
and mobile navigation. `VITE_API_BASE_URL` can override the default
`http://127.0.0.1:8000`; keep the frontend origin at localhost/127.0.0.1:5173 to
match the unchanged backend CORS allowlist.

1. The selected node's prepared synthetic historical input is loaded once through
   GET `/api/c2/microclimate/demo-input`, sample index 0.
2. Choose NODE_01/NODE_02 and Attention BiLSTM/LSTM/GRU, then **Run forecast**.
3. POST `/api/c2/microclimate/forecast` receives the original 336 observations and
   their original quality flags. No future observations, labels or uncertainty
   intervals are created. Backend INPUT scaling, frozen inference and TARGET
   inverse transformation remain authoritative and unchanged.
4. Select 24h, 72h or 168h to view cumulative forecast hours 1–H locally. All model
   responses contain 168 future hourly steps. Horizon changes do not issue new
   requests.
5. **Compare all 3 models** explicitly requests predictions using identical
   historical inputs. The table compares original-unit mean forecasts; it is not
   an accuracy ranking.

Changing node cancels obsolete requests and clears prior-node results. Model
changes clear the selected-model forecast. Request timeouts, cancellation,
missing backend, malformed contracts and controlled API failures have explicit
handling. There is no polling and no automatic model inference on page load.

## Visual and accessibility design

Nature-inspired greens, warm photographic accents, a typographic hero, restrained
surfaces and clear research-status messaging extend the existing green theme.
Three overview cards derive means and ranges exclusively from the selected
forecast's returned values; empty states show no invented readings.

SVG charts plot all 336 historical hours by default and the selected forecast
window. Historical inputs are muted solid lines; forecasts are colored/dashed,
with an origin marker and exact hourly inspection. Clean WARN is usable; INVALID,
anomalous and supplied-imputed historical rows use the same bounded causal fill
as the API and appear with amber markers and filled-input labels. This display
operation never changes the observations sent to the server.

History view controls zoom to 14 days, 3 days or 24 hours. Pointer inspection and
keyboard-accessible range sliders expose exact values and timestamps. Mobile
charts retain readable axes in a horizontally scrollable viewport; the point
inspector works without hover. Times are explicitly Asia/Colombo (UTC+05:30).
Soil moisture remains **INDEX**, never volumetric water content or percent.
Controls use native labels, pressed states, focus outlines and live status/error
messages. Layout breakpoints cover desktop, tablet and mobile. Nonessential
CSS motion and automatic 3D orbit respect reduced-motion preferences.

## Optional conceptual 3D

Three.js **0.186.1** is the only new runtime package. React Three Fiber and Drei
were unnecessary for this bounded scene, so the React stack stays unchanged.
The existing project uses JavaScript/JSX; it was not migrated to TypeScript.

The scene shows 24 stylized pepper plants, four rows, three soil strata,
conceptual irrigation lines, two sensing nodes and a small monitoring station.
OrbitControls supports mouse/touch orbit and bounded zoom. Keyboard-accessible
rotate/zoom buttons and pause-orbit controls are provided. Sensor hover labels
describe the concepts; selecting a node highlights it and changes the forecast
node. No connectivity status or sensor measurements are invented.

The entire scene is loaded lazily as it approaches the viewport. WebGL2 absence,
context loss or module/render errors fall back to an original static SVG diagram;
**Use static view** also allows users to opt out. Forecasting does not depend on
the scene. It uses low-poly shared geometries/materials, one 512px shadow map,
pixel ratio capped at 1.5 and a low-power context preference. Idle orbit is capped
at approximately 25 updates/second, stops when offscreen/hidden and is disabled
for reduced motion. Resources, listeners, observers and animation frames are
disposed on unmount. Every view labels the farm as conceptual, not installed.

## Reference photographs and offline use

All runtime images are optimized local WebP assets with responsive sources,
reserved dimensions and below-fold lazy loading. No runtime image, font, weather
or hardware connection to the internet is needed. External attribution links are
informational.

| Reference | Author / verified license | Scientific context |
|---|---|---|
| [Capsicum chinense](https://commons.wikimedia.org/wiki/File:Capsicum_chinense_(Solanaceae).jpg) | Filo gèn’, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | Species reference; Sri Lankan Nai Miris cultivar not independently verified |
| [Drip irrigation](https://commons.wikimedia.org/wiki/File:Drip_irrigation_(2552390830).jpg) | Dwight Sipler, [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) | Cherry tomato cultivation and wetted soil, explicitly not Nai Miris trial evidence |
| [Weather station](https://commons.wikimedia.org/wiki/File:Weather_station.png) | USDA Forest Service, US public domain per source declaration | Third-party station, explicitly not our C1 device |

Visible credits and [asset attribution](../../frontend/src/assets/c2/microclimate/ATTRIBUTION.md)
record sources, license links, resizing, WebP conversion and display cropping.
The adapted botanical images retain CC BY-SA 4.0.

## Executed verification

From `frontend/`:

```powershell
npm run build
npm run test:c2
npm run test:microclimate:render
npm run test:microclimate:live
```

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m unittest app.c2.microclimate.api.tests.test_api -v
```

| Check actually executed | Result |
|---|---|
| Production build | Passed; no oversized-chunk warning after separating the optional renderer |
| Frontend Node tests | 21 passed, 0 failed: 13 new Microclimate and 8 unchanged Yield tests |
| React server-render checks | Page markup, 9 variable/horizon chart combinations and static SVG fallback passed; no React render errors |
| Real local HTTP through the frontend API client | All 3 models × 2 nodes passed: 168 finite future steps, valid ordering/units/slices, preserved history masks and all horizon summary counts |
| Previous API output consistency | Attention BiLSTM NODE_01 maximum original-unit difference 0.0 |
| Existing Yield live API | HTTP 200, 275.59 g/plant on the existing example |
| Backend API regression tests | 24 passed, 0 failed in 31.892 seconds; all 6 model/node saved-output comparisons remained exactly equal |
| Browser-origin CORS | Existing allowlist accepted the local Vite origin |
| Vite routes, transformed page/scene modules, all 3 used photographs | HTTP 200 with expected HTML/JavaScript/WebP content types |
| CSS syntax validation | 0 warnings |
| `git diff --check` | Passed |
| Browser desktop/mobile/WebGL rendering and browser console | **NOT VERIFIED**: browser inventory empty; attempts to create in-app and Chrome tabs both returned browser unavailable |

The render checks are server rendering, not a browser simulation or proof of GPU
rendering. Static fallback markup is verified; actual device fallback transitions,
touch behavior, visual contrast, mobile overflow and browser console still need a
human browser smoke test. There was no pre-existing ESLint or TypeScript setup;
no lint/typecheck pass is claimed. Vite/esbuild parsed the JS/JSX/CSS and the
automated tests exercised the data and rendering contracts.

Production chunk sizes are approximately: application entry 296 kB / 94 kB gzip,
Microclimate page 29 kB / 10 kB gzip, farm UI/controls 27 kB / 8 kB gzip, optional
Three core 168 kB / 46 kB gzip and optional renderer 358 kB / 88 kB gzip. No Three
chunk is imported by the application entry. Images are approximately 12–210 kB
each; the larger irrigation source is requested only when responsive sizing needs it.

## File inventory and boundaries

Added:

- `frontend/src/pages/c2/MicroclimateForecasting.jsx`
- `frontend/src/components/c2/microclimate/{ClimateIcon,ForecastChart,FarmPanel,FarmScene}.jsx`
- `frontend/src/services/c2/microclimateApi.js`
- `frontend/src/styles/c2/microclimate.css`
- Five optimized WebP files and `ATTRIBUTION.md` under `frontend/src/assets/c2/microclimate/`
- `frontend/tests/c2/microclimateApi.test.mjs`, `microclimateRender.mjs`, `microclimateLive.mjs`
- `frontend/package-lock.json` and this document

Modified: `frontend/package.json`, `frontend/vite.config.js`, `frontend/src/App.jsx`,
`frontend/src/components/Navbar.jsx`, `frontend/README.md`.

The new lockfile supports reproducible installs with `npm ci`. No backend package
was installed. All backend source, datasets, checkpoints, scalers, previous
experiments, Yield-specific frontend files and C1/C3/C4 files are protected by a
before/after SHA-256 comparison. Audit evidence is outside the repository at
`%LOCALAPPDATA%/C2DashboardAudit/20261021/`.
The final audit checked 330 pre-existing files: 325 remained byte-identical,
exactly the five frontend files listed above changed, and none were missing.
All backend and existing experiment files matched their pre-task hashes.
No training, model changes, external dataset integration, commits, pushes,
publishing or deployment were performed.
