# C2 PP1: local RBAC, farms and location-aware selection

**Site-wide update:** [Central authentication integration](PP1_Sitewide_Authentication.md)
supersedes the anonymous-demo and page-local-login workflow described below.
All application routes now require login; legacy research APIs require
Admin/Researcher access. Existing database records and farm permissions remain.

**Synthetic Data — Prototype Evaluation Only**

Implemented and executed on branch `feature/c2-predictive-intelligence` using
`backend/.venv`. This extends the existing FastAPI application and React pages;
it does not replace the trained forecasting implementation.

## Actual implementation and permission boundary

Inspection found no existing authentication, session store, user registry,
farm database or map library. FastAPI/Pydantic, React/React Router, Python's
`sqlite3`, `hashlib`, `hmac` and `secrets` are reused. No package was installed.

Protected operations live under **`/api/c2/access/`**. Their backend dependencies
check authentication, role, farm membership and the selected farm/site/node
relationship. Guessing another farm's identifier does not confer access.

| Operation | Admin | Researcher | Farmer / Viewer (`viewer`) |
|---|---|---|---|
| Manage users, roles and account status | Yes | No | No |
| Create/update farm metadata, create/rename sites, register/assign nodes | Yes | No | No |
| View farm catalog | All farm metadata for administration | Assigned farms only | Assigned farms only |
| View farm history / saved forecasts | Membership required | Membership required | Membership required |
| Run and persist a farm forecast / model comparison | Membership required | Membership required | No |

Admin management scope is global, but protected history and forecast access still
requires an explicit farm membership. Creating a farm grants membership to its
creating Admin. New users have **no farm memberships** until an Admin grants them.
Membership is an access assignment, not a claim of legal land ownership.
Role/status changes revoke that user's sessions. Membership changes take effect
on subsequent requests without waiting for a token refresh. Removing the last
active Admin is rejected. Farm/node membership is rechecked before inference and
before saving its result; account role/status is also rechecked before saving.

The frontend role indicator, hidden Admin link, disabled Viewer execution/model
controls and protected Admin page supplement these backend checks. They are not
the security boundary. `/predictions/manage` renders an access-required state for
non-Admins; direct management API calls return 401/403 as appropriate.

The prior stateless APIs remain compatible:

- `GET /api/c2/microclimate/demo-input` serves only the existing synthetic demo.
- `POST /api/c2/microclimate/forecast` remains public stateless prototype inference
  on caller-supplied histories; it cannot retrieve the new farm catalog, memberships
  or saved forecasts. It is **not** a protected farm-data API.
- Yield Prediction behavior remains unchanged.

Public synthetic-demo mode is explicitly labeled and separately selectable. It
provides no access to private farm records. An anonymous visitor can still select
the two synthetic nodes and run the original demonstration. Farm-scoped Viewer
execution is always denied by the protected API. Keeping the older public service
does not make private farm storage public; it also means RBAC is not a restriction
on all possible independent/stateless use of the trained models. Keep the entire
PP1 app on loopback; public deployment needs a separate policy and resource limits.

The design follows backend checks on every protected request and combines role
with resource relationships, rather than treating a role name as ownership.
References: [OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html),
[FastAPI dependency/scopes patterns](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/).

## Passwords, sessions and local storage

- Passwords use PBKDF2-HMAC-SHA256, 600,000 iterations and a random 128-bit salt.
  Password hashes are compared with constant-time comparison. There is no default
  account/password, JWT signing key or credential in source.
- Sessions use random 256-bit opaque tokens. Only SHA-256 token hashes are stored
  in SQLite; the raw token is in an HttpOnly, SameSite=Strict cookie, scoped to
  `/api/c2/access`. Sessions expire after 8 hours and after 30 minutes of inactivity.
  Successful login rotates the browser's previous session; logout revokes it.
- Mutations require a session-bound CSRF token supplied in `X-CSRF-Token`.
  The frontend keeps it in memory and refreshes it through `/me`. No session token
  is put in localStorage, URLs or the JSON login response.
- Access routes reject non-loopback client addresses, unexpected Host names and
  unexpected Origin headers. Credentialed CORS allows only the existing local
  frontend origins. PUT was added for management operations; GET/POST remain.
- Login attempts are limited to 5 per username/client and 20 total per client in
  15 minutes. Unknown and incorrect accounts receive the same login failure.
  Private payloads are limited to 16 KiB, validation errors omit input values,
  and access responses use `Cache-Control: no-store`.

The session cookie intentionally uses `Secure=False` for this **loopback HTTP**
workflow. This is not an internet authentication deployment. Do not put it behind
a public proxy or bind the server to `0.0.0.0`. HTTPS/Secure cookies, a reviewed
identity provider, recovery/MFA, stronger throttling and operational auditing are
post-PP1 work. CORS is not authorization. See
[OWASP REST guidance](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html).

Default persistence is outside the repository:
`%LOCALAPPDATA%/SmartAgricultureC2/access.sqlite3`. `C2_ACCESS_DB` optionally selects
a different local SQLite path. The file contains users/hashes, sessions, login
attempts, farms, memberships, sites, node registries and new saved forecast records.
It does not overwrite any existing experiment output. Protect the file and its
backups with the operator's OS access controls. It is not encrypted at rest.

## Farm/site/node and location model

`farms` stores `farm_id`, `farm_name`, `district`, `latitude`, `longitude`, IANA
`timezone`, `crop_type`, nullable `growth_stage`, immutable `is_demo` classification
and server-controlled provenance. `sites` has a stable `site_id`, parent `farm_id`
and editable site name. The displayed location is the supplied **farm** location;
individual sensor GPS or site boundaries are not inferred.

Each registered `node_id` has at most one assigned site, immutable source/demo
classification, sensor metadata and an optional calibration reference. The node's
farm is derived through its site, not independently trusted from the client.
Foreign keys and parameterized SQL enforce relationships. Memberships join users
to farms. Saved forecasts include farm/site/node IDs, creator, creation time,
model ID, input fingerprint and the complete original-unit response/provenance.
The UI retrieves the latest 20 saved forecasts for the exact selected site/node.

Coordinates must be finite, paired and within latitude [-90,90], longitude
[-180,180]. Booleans, unpaired values, invalid timezones and unknown fields are
rejected. Coordinates are nullable rather than fabricated. Supplied metadata is
marked `operator_supplied_unverified`; validation is not independent GPS proof.
Optional growth stage records what an authorized operator supplies, not an inferred
label; it never enters current model inputs.

Only one explicit **PP1 synthetic demonstration** farm is seeded, with two
synthetic sites containing the unchanged `NODE_01` and `NODE_02` identities.
Coordinates and growth stage remain null. Attempts to give demo records coordinates
or stage labels, or to assign synthetic nodes to non-demo farms, are rejected.
The UI shows **“Demo node — location not verified”**. A newly registered non-demo
node has no observation source; identifier registration does not authenticate a
physical device or prove calibration.

For supplied non-demo coordinates, the UI renders an offline equirectangular
coordinate locator with labeled latitude/longitude grid. This is a coordinate
visualization, not a surveyed field-boundary or street map. No location is sent
to an external tile/geocoding service and no map dependency was added.

## Forecast selection and scientific limitations

Farm selection retrieves only authorized farm metadata. Site/node selection is
checked against the persisted mapping. A protected forecast request contains only
the selected site, node and model IDs. The server retrieves the associated input;
it does not accept client-substituted farm histories.

For demo nodes, the server reuses the existing `demo_input()` mechanism: actual
336-hour historical inputs from the original synthetic dataset, original quality
flags and exact prepared-tensor checks. The original `prepare_history()` and
frozen INPUT/TARGET scalers are reused. The original `[1,336,3] → [1,168,3]`
inference is called with `training=False`. No future labels are retrieved as inputs.

For non-demo nodes, no verified C1 history is currently ingested. History retrieval
and inference return **409: historical data unavailable**, instead of silently
substituting NODE_01, NODE_02 or another farm's history. Mismatched mappings return
404. Farmer/Viewer users can inspect assigned histories and available saved results,
but cannot execute protected forecasts or change models. Results are stored only
after successful, authorized inference.

Latitude, longitude, district, farm/site/node IDs and growth stage are **not learned
features**. Identical historical measurements produce the same forecast regardless
of location metadata. Different legitimate node histories can produce different
forecasts. This implements **location-aware history selection**, not
coordinate-conditioned ML, field validation or a location-based output adjustment.
The existing model/API timezone remains Asia/Colombo; farm timezone metadata does
not change trained preprocessing or synthesize another region's history.

True geographical conditioning requires verified multi-site observations with
location/time/units/calibration provenance, enough seasonal coverage, observed
crop-stage labels where proposed, a research-approved feature/model revision and
new training-only scalers. Evaluation must include chronological and held-out-site
generalization. NASA POWER/ERA5-Land compatibility, spatial/temporal resolution and
availability timestamps need verification before integration. None is integrated
here. Soil moisture remains INDEX, not calibrated volumetric water content.

## Startup and PP1 workflow

From `backend/`, create the first Admin interactively **once**:

```powershell
.\.venv\Scripts\python.exe -B -m app.c2.access.bootstrap
```

Choose your own username and a 12–128-character password; the password is entered
through `getpass`, not an argument or source file. Bootstrap refuses an existing
user database. No real operator account was created automatically during this
implementation; test credentials existed only in disposable temporary databases.

Start the existing backend:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From `frontend/`, run `npm run dev`. Open
`http://localhost:5173/predictions/microclimate` or consistently use `127.0.0.1`
for both browser/backend hosts. The access client matches the browser hostname by
default so SameSite cookies work. If overriding `VITE_API_BASE_URL`, keep the same
hostname; mixing localhost and 127.0.0.1 for credentialed requests is unsupported.

1. Public mode still runs the original synthetic demonstration.
2. Sign in with the bootstrapped Admin. Open **Manage users, farms & nodes**
   (`/predictions/manage`). Create Researcher and Viewer accounts with chosen
   passwords, and grant their farm memberships explicitly.
3. Select the demo farm/site/node. Run a forecast as Admin/Researcher or compare
   all three checkpoints. Saved results are then available to assigned Viewers.
4. Sign out and sign in as Viewer to demonstrate read-only saved-result access.
   Management and protected forecast execution are denied by the backend even
   when called directly.
5. Create real farm metadata only from information you genuinely possess. Register
   and assign its actual node identifier; until C1 history exists the correct result
   is unavailable data. Do not populate imaginary coordinates for the viva.

## Executed checks

```powershell
# backend/
.\.venv\Scripts\python.exe -B -m unittest app.c2.access.tests.test_access app.c2.microclimate.api.tests.test_api -v

# frontend/
npm run build
npm run test:c2
npm run test:microclimate:render
```

| Evidence | Actual result |
|---|---|
| Access/security tests | 18 passed, 0 failed; final access run 22.447 seconds |
| Existing Microclimate API regressions | 24 passed, 0 failed; combined 42-test run passed |
| Frontend tests | 27 passed, 0 failed: 6 access + 13 Microclimate + 8 Yield |
| Protected inference, 3 models × 2 demo nodes | 168 finite three-target outputs each; max absolute difference from saved outputs **0.0** |
| Existing public inference comparisons | All 6 model/node comparisons remained exactly equal |
| Yield Prediction | Existing valid/invalid API regression tests passed |
| Session and security coverage | No default users; hashed passwords/tokens; CSRF; hostile Origin/Host; non-loopback denial; expiry/revocation; login throttling; body limit; password-error redaction |
| RBAC/data coverage | Admin user/farm/site/member/node operations; non-Admin denials; other-farm isolation; immediate membership revocation; cross-site/node rejection; invalid coordinates; no C1-to-demo fallback |
| Frontend build | Passed, no oversized chunks; optional Three core/renderer remain lazy |
| React server rendering | Page, 9 charts, static farm fallback, 3 role states, Admin access-required state and coordinate locator passed without React errors |
| Live restarted server | Protected `/farms` and `/me` returned 401 without a session; `/health`, dashboard/admin HTML routes and transformed Admin module returned 200 |
| Hash preservation | 267 protected files, including model/data/scaler/result files, Yield files and original C4 assets, matched the earlier pre-dashboard SHA-256 baseline |
| Browser/mobile UI interaction | **Not reverified**: current browser/app inventory is empty. Prior manual checks covered the earlier dashboard, not these new screens. CSS mobile breakpoints and server rendering were checked, not a real browser. |

An initial combined test run exposed shared model-cache state between test suites;
the new access tests now save/restore their runtime cache so the unchanged legacy
cold-load assertions remain meaningful. A test archive key mismatch was corrected.
Final runs pass; no saved-output files were modified. Existing TensorFlow/Starlette
deprecation/native-CPU notices remain; no dependency upgrades were attempted.

## Files and remaining scope

Added `backend/app/c2/access/` (`schemas.py`, `store.py`, `routes.py`, `http.py`,
`bootstrap.py`, tests), frontend `accessApi.js`, `FarmAccess.jsx`,
`FarmManagement.jsx`, `access.css`, `accessApi.test.mjs`, and this document.
Updated `backend/app/main.py`, `frontend/src/App.jsx`, the existing Microclimate
page/farm components and rendering tests. Existing ML implementation, source CSV,
trained checkpoints, scalers and experiment results are unchanged.

This is an implemented **local PP1 access system**, not production deployment.
Remaining work includes real C1 device authentication/ownership proof, ingestion,
durable quality/staleness policy for field history, calibration validation,
location/stage provenance verification, backup/recovery, audit/monitoring,
password reset/MFA/identity-provider review and internet-facing resource controls.
SQLite access is protected by OS ownership, not encryption or separate DB roles.
There is no forecast-retention cleanup; APIs return only the latest 20 matches but
stored rows remain until a future authorized retention policy is implemented.
No packages were installed, no model was trained, and nothing was committed,
pushed, published or deployed.
