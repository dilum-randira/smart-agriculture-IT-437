# Microclimate runtime recovery — 22 October 2026

Synthetic Data — Prototype Evaluation Only

## Evidence and diagnosis

Read-only SQLite queries confirmed active `farmer1` (internal role `viewer`, displayed as Farmer) already belongs to `pp1_synthetic_demo`. That farm contains `demo_site_node_01` / `NODE_01` and `demo_site_node_02` / `NODE_02`. No credentials or memberships were changed. Coordinates remain null; these are synthetic observation identities.

An independent authenticated session through the running backend returned the assigned farm, both site/node mappings, 336 actual prepared historical observations for each node, and saved forecasts. Thus a missing database membership, missing history, and a currently unreachable backend are ruled out for farmer1 in these checks. The screenshot's actual browser identity, cookies, console and failing request were unavailable: its exact runtime trigger is NOT conclusively established.

Confirmed frontend failure paths:

- Farm retrieval failure displayed both an error and an unsupported “No farms assigned” message. There was no assignment retry or focus refresh. Empty farm state prevents site/node selection, so history never loads and Run remains disabled.
- Initial selection inspected only the first farm/first site, even when another authorized site contained nodes.
- `Promise.all` coupled historical loading to saved-result retrieval. One rejected saved-result request discarded successful historical data and disabled inference.
- The real 3D panel was initially collapsed below the charts; only a small static preview was visible. Numerous dashboard font rules used 8–12px.

## Changes in this step

Modified:

- `frontend/src/components/c2/microclimate/FarmAccess.jsx`: explicit retrieval-error vs unassigned states, Admin assignment guidance, manual/focus refresh, authorized selection preservation and identity-change cleanup.
- `frontend/src/pages/c2/MicroclimateForecasting.jsx`: independent history/saved-result outcomes; refresh does not clear an existing forecast when the authorized selection remains unchanged.
- `frontend/src/components/c2/microclimate/MicroclimateDashboardView.jsx`: real supporting 3D scene in the right-side header; all three historical/forecast charts and existing controls retained.
- `frontend/src/components/c2/microclimate/EnvironmentContext.jsx`: expanded by default, still collapsible; actual lazy-loaded WebGL component and accessibility fallback retained.
- `frontend/src/styles/c2/referenceWorkspace.css`: larger controls, type and KPIs, wider desktop workspace, visible 300px-high supporting scene, responsive stacking. Amber temperature, blue humidity and green soil accents retained.
- `frontend/tests/c2/microclimateRender.mjs`: updated structural expectations and additional failure/unassigned-state checks; existing chart, date, role and interaction checks retained.

Added:

- `frontend/src/services/c2/farmSelection.js`: reusable authorized selection and independent workspace-loading logic.
- `frontend/tests/c2/farmSelection.test.mjs`: five focused regressions.
- `frontend/tests/c2/farmWorkspaceLive.mjs`: real authenticated frontend-client checks against farm-scoped endpoints; credentials supplied privately through environment variables.
- This report.

No backend implementation, authentication policy, credentials, memberships, model, scaler, dataset or original experimental output was changed. Live forecast verification added six ordinary saved forecast records through the existing authorized API, and used/revoked its own verification sessions.

## Verification

- Frontend unit tests: **62 passed, 0 failed**.
- Frontend server-render verification: passed, including nine horizon chart renders, 42 day-specific chart renders, three single-hour charts, farm error states, role navigation, Yield page and environment toggle states. This is not browser automation.
- Backend access and inference regression tests: **58 passed, 0 failed**, in 56.709 seconds. Saved-output maximum difference **0.0** for all three models on both nodes.
- Real authenticated frontend API client: **six model/node combinations passed**, each using 336 historical hours and producing 168 finite hourly predictions. The 24/72/168-hour calendar groups preserve exact counts. Initial selection is the sample farm / NODE_01 site / NODE_01. NODE_02 is selected through its own site.
- Farmer Admin endpoint request: **403**; Yield prediction: **200**.
- Vite production build: passed. Local installed farm asset: HTTP **200**.
- Protected file hashes: **250/250 unchanged**; installed asset pack: **268/268 unchanged**. `git diff --check` passed. Existing unrelated working-tree changes were preserved.
- Existing backend warnings: Starlette/httpx deprecation and TensorFlow CPU/deprecation messages. No packages were installed to silence them.

Browser inventory exposed no available browser or app. No actual 1440px or 390px screenshots, browser click-through, console inspection or WebGL visual verification were possible. Do not describe the API/markup checks as proof of those browser behaviors or claim visual parity with the supplied reference.

## Reproduction

From the repository root, in separate terminals:

```powershell
Set-Location backend
.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1
```

Use the same hostname for the login and dashboard (for example `http://127.0.0.1:5173/login`). Existing sessions and credentials remain in use. On the Microclimate page, Refresh farm assignments fetches the account's server-authorized farms; it does not grant access. A genuinely unassigned account must ask an Admin to open Farm management and assign that account to the existing farm. Creating an empty real farm does not manufacture historical sensor data.

Checks from `frontend`:

```powershell
npm run test:c2
npm run test:microclimate:render
npm run build
# Supply C2_TEST_USERNAME and C2_TEST_PASSWORD privately; never echo them.
node tests/c2/farmWorkspaceLive.mjs
```

Backend checks from `backend`:

```powershell
.venv\Scripts\python.exe -B -m unittest app.c2.access.tests.test_access app.c2.microclimate.api.tests.test_api
```

Remaining browser acceptance: sign in with the existing account, verify automatic farm/site/node selection and historical charts, execute each model and comparison, change sites to inspect NODE_02, inspect day/horizon controls, and verify the live 3D scene and overflow at 1440px and 390px. No real-field accuracy or weather conditions are inferred from this synthetic demonstration.
