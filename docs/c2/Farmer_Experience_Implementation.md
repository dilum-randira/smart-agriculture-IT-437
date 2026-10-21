# Farmer experience and access control

Implemented on `feature/c2-predictive-intelligence`. This document supersedes the earlier rule that Farmer/Viewer cannot execute farm forecasts. Internal database role `viewer` is retained; its product label is **Farmer**. No credentials are documented here.

## Account and farm lifecycle

- Login: `/login`; self-registration: `/register`. Registration persists a genuine account in the existing SQLite database, using the existing PBKDF2 password hashing. It does not log the account in automatically: success links to login.
- Server registration accepts only username and password (12–128 characters). Extra fields, including a role, are rejected. New accounts always receive `viewer`, without any farm or node assignment.
- Registration requires an allowed browser Origin, remains loopback-only, and allows five registration attempts per client in 15 minutes. Failed uniqueness attempts also count. Existing login throttling, HttpOnly/SameSite cookies, session expiry/revocation and authenticated CSRF checks remain in place.
- Existing `farmer1` is assigned to the existing `pp1_synthetic_demo` farm. Its original sites `demo_site_node_01` and `demo_site_node_02` still contain `NODE_01` and `NODE_02` respectively. No duplicate farms, invented coordinates or physical devices were created.
- Existing account/password/session/farm/site/node/forecast rows were compared before and after assignment and preserved. A verified SQLite backup was made outside Git under `%LOCALAPPDATA%/SmartAgricultureC2/backups/` before the additive schema update and membership grant.

## Permissions

| Capability | Farmer (`viewer`) | Researcher | Admin |
|---|---|---|---|
| Read assigned farm/site/node information and saved forecasts | Yes | Yes | Yes; management also lists all farms |
| Run all three microclimate models for an assigned node | Yes, if history exists | Yes, if history exists | Yes, if history exists |
| Create a regular farm | Yes; ownership + membership assigned automatically | No | Yes |
| Edit regular farm metadata | Only its owner while still a member | No | Yes |
| Edit shared sample farm metadata | No | No | Yes, existing synthetic safeguards apply |
| User/role, membership, site or node administration | No | No | Yes |
| Manually entered Yield Prediction | Yes | Yes | Yes |
| Legacy unscoped microclimate research APIs | No | Sample-farm membership required | Yes |

Membership grants read/forecast access; it does not grant farm ownership. The additive `farm_owners(farm_id, user_id)` table records ownership for newly created farms. Ownership of existing farms is not guessed from membership. All existing data tables remain intact. Every farm update checks ownership on the backend inside its transaction; creation cannot choose another owner. Farmers cannot assign nodes, create synthetic farms, change roles or grant memberships. Farm deletion is intentionally unavailable (405), avoiding destructive operations in this step.

Farm-scoped forecasts revalidate membership, farm/site/node association and current role before saving. A different Farmer with no membership receives 404 for histories/forecasts/updates and cannot list the farm. Revoking membership takes effect immediately. Saved forecasts are shared with authorized members of the selected farm, rather than private per-user records.

## Data and prediction boundaries

- All sample observations remain synthetic. Visible **Sample Data — Not Live Sensor Readings** indicators accompany the farm context; scientific inference responses retain their original `Synthetic Data — Prototype Evaluation Only` label and provenance.
- Models/scalers are unchanged: 336 historical hourly steps, three environmental variables, 168 future hourly steps. The UI selects cumulative 24h/72h/168h slices. Identical inputs reproduce saved predictions with maximum original-unit difference **0.0** for all six model/node combinations.
- A regular new farm has no sites/nodes/readings until configured. Registered real nodes without verified history receive an unavailable-data response; sample observations are never substituted.
- Coordinates and observed growth-stage metadata do not enter the frozen models. Coordinate pairs/ranges/timezones are validated. The offline locator makes no field-boundary claim; an optional OpenStreetMap link shares coordinates only when explicitly opened. Sample farms have no coordinate link.
- Yield Prediction accepts five manually supplied plant traits. There is no farm identifier, private-record retrieval or saved Yield history in that API; access is authenticated and role-level with CSRF, **not farm-isolated**. The existing served predictor is tuned XGBoost. Existing Random Forest/SVR comparison material and model artifacts are preserved; no new RF/SVR serving API is claimed. The page retains units and published-data/field-validation limitations. New user entries are not added to training data.

## Navigation and user experience

- `/`: username greeting, assigned farm/site/node counts, actual data availability, links to tools, and recent saved forecasts (latest six across up to eight assigned nodes).
- `/farms`: assigned farm inventory, create regular farm, edit owned regular farms, coordinate locator, actual sites/nodes and empty states.
- `/monitoring`: actual assigned sensor/data availability and links to existing historical charts. No fake live readings.
- `/sensors`: assigned sites/nodes, sensor metadata/calibration references and unavailable-history states. Registration/assignment remains Admin-only.
- `/account`: username/role; no self-service privilege escalation.
- `/predictions/microclimate`: shared selectors, three frozen models, horizons, saved results, charts and existing interactive/static farm.
- `/predictions` (also `/predictions/yield`): existing Yield form and evidence/comparison panels.
- `/predictions/manage`: existing Admin user/farm/site/node/membership management.

The shared auth provider and route guard are reused. Login preserves only known internal destinations. The header has active links, current identity/role, logout and a keyboard-accessible mobile menu. Green/cream styles, responsive grids, loading/error/success/empty states and focus outlines use existing dependencies. Legacy research placeholder routes remain reachable by their authorized roles; they do not claim implemented device ingestion or private farm data.

## Changed files

- Backend: `app/main.py`, `app/c2/access/{schemas,store,routes}.py`, `app/c2/access/tests/test_access.py`.
- Frontend: `src/App.jsx`, `src/auth/policy.js`, `src/components/Navbar.jsx`, `src/components/c2/microclimate/FarmAccess.jsx`, `src/pages/Login.jsx`, `src/pages/Register.jsx` (new), `src/pages/c2/FarmWorkspace.jsx` (new), `src/pages/c2/{MicroclimateForecasting,YieldPrediction}.jsx`, `src/services/c2/farmSummary.js` (new), `src/styles/c2/farms.css` (new).
- Tests: `tests/c2/{accessApi,authPolicy}.test.mjs`, `tests/c2/farmerExperience.test.mjs` (new), `tests/c2/microclimateRender.mjs`.
- Documentation: this document; earlier site-wide guide links here for updated Farmer permissions.

## Verification and reproduction

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m unittest app.c2.access.tests.test_access app.c2.microclimate.api.tests.test_api -v
.\.venv\Scripts\python.exe -B -m unittest app.c2.microclimate.preprocessing.tests.test_phase1 app.c2.microclimate.preprocessing.tests.test_phase1_masked app.c2.microclimate.preprocessing.tests.test_scaling -v
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From `frontend/` (a separate terminal for `dev`):

```powershell
npm run build
npm run test:c2
npm run test:microclimate:render
npm run dev
```

Executed results: **58 access/API tests + 54 preprocessing tests passed**, **38 frontend tests passed**, production build passed, render checks passed (nine chart combinations, three roles, registration, five farm/account views and mobile-menu markup). Tests use temporary SQLite databases and random credentials, not the real Admin account. No model training tests or training commands were run.

The restarted loopback server was also checked over real HTTP using farmer1: login, `/me` refresh, actual assignments, 336-hour histories, all three models for both nodes, 24/72/168-hour output slices, saved histories, Yield (existing regression fixture: 275.59 g/plant), and logout/session revocation all passed. Forecast maximum difference from saved outputs was 0.0. Six new operational saved-forecast records were added by this verification; no previous records or experiment artifacts were overwritten. SHA-256 checks confirmed all 250 protected data/model/preprocessing/experiment files in the pre-change inventory were unchanged.

## Remaining manual checks and limits

Browser tooling is unavailable. Actual login/registration interactions, password-manager behavior, keyboard focus, mobile menu/overflow at 360px/768px and WebGL interaction must be manually checked. Render and HTTP tests do not establish those browser outcomes. Open the app using the same hostname for frontend/backend (recommended `127.0.0.1`). Sign in with an existing account; never rerun bootstrap or reset the database.

Manual sequence: sign in as farmer1 → confirm one sample farm/two sites/two nodes → select each site/node → run each model → switch 24/72/168h → view saved history → open Yield → create a regular farm with truthful details → confirm unavailable data → edit it → logout/refresh → confirm login required. Register a separate account and confirm it has no inherited sample-farm access. Sign in as Admin to grant membership; Researcher/Farmer must be denied Admin management.

This remains a local application: HTTP cookies are intentionally non-Secure for loopback development, no email verification/recovery/MFA is implemented, registration throttling is local-client based, and hardware ingestion/authentication is not implemented. Internet deployment needs HTTPS/Secure cookies, deployment-aware origin/session policy, durable abuse controls and operational monitoring. No real field accuracy, real sensor availability or coordinate-aware prediction is claimed. No packages installed, model/data artifacts changed, training, commits, pushes or deployment performed.
