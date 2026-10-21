# Updated Farmer permissions

The Farmer experience now supports assigned-node forecast execution, owned-farm creation/editing and least-privileged registration. See [Farmer experience implementation](Farmer_Experience_Implementation.md) for the current policy and verification. Earlier statements below that deny all Farmer execution or public registration describe the prior implementation.

---

# PP1 site-wide authentication integration

Implemented on `feature/c2-predictive-intelligence` using the existing SQLite
database, accounts, PBKDF2 password hashes, opaque sessions and CSRF protection.
No new authentication system, database, account or dependency was introduced.
The existing Admin account is retained. **Do not rerun bootstrap or reset the DB.**

## Login and shared layout

Open **http://127.0.0.1:5173/login**. The responsive green/cream page has username
and password fields, show/hide password, loading and generic credential-error
states, and no registration or prefilled credentials. Sign in with your existing
account. The default destination is Overview; protected-route links preserve their
intended destination through login. Redirect destinations must be known internal
routes; external/protocol-relative URLs, login loops, backslashes and control
characters are rejected. Case/trailing-slash/encoded route forms share the same
permission rules.

`AuthProvider` restores identity through the existing `/api/c2/access/me` endpoint.
It centrally handles login, logout, route/focus session checks and 401 events from
all C2 API clients. `RequireAuth` gates the application layout, shows restoration
or connection-error/retry states, redirects anonymous users to `/login`, and sends
authenticated unauthorized roles to `/access-denied`. Failed backend connectivity
does not produce a redirect loop or an empty screen. No interval keeps inactive
sessions alive; server expiry/revocation remains authoritative.

The existing Navbar retains its branding and responsive menu, with signed-in
username, role and Logout. Navigation and Overview cards use the same role policy
as the route guard. Logout waits for server revocation; a network failure is shown
instead of falsely reporting a successful logout. Already-expired sessions return
to login. Microclimate-specific login/logout controls were removed. Farm management
and Microclimate consume the shared identity rather than restoring separate sessions.

## Explicit access policy

| Section / operation | Admin | Researcher | Farmer / Viewer |
|---|---|---|---|
| Overview | Yes | Yes | Yes |
| Monitoring | Read-only placeholder | Read-only placeholder | Read-only placeholder |
| Microclimate / assigned farm information | Farm membership required | Farm membership required | Farm membership required |
| Assigned saved forecasts | Read | Read | Read |
| Protected farm forecast execution / comparison | Yes, with membership | Yes, with membership | No |
| Yield (`/predictions`, alias `/predictions/yield`) | Yes | Yes | No |
| Irrigation / Integration / Harvest & Market | Research placeholders | Research placeholders | Access denied |
| `/predictions/manage` | Admin management | Access denied | Access denied |

Monitoring and the other unimplemented modules contain no live/private farm data.
No farm-level isolation is claimed for these placeholders. Integration is an honest
placeholder route, not a new device integration. No C1/C3/C4 component was rebuilt.
Any separately hosted legacy component requires its own integration/security review.

Yield and the legacy synthetic research API do not have farm ownership fields.
Their conservative policy is **authenticated Admin/Researcher only**, with CSRF
for execution, rather than pretending a farm selector creates ownership isolation.
They cannot retrieve the new farm database. Farm-scoped history/forecast routes
retain their stronger role + membership + exact site/node checks. Viewer requests
cannot bypass those restrictions through the older unscoped APIs.

The earlier anonymous synthetic-demo workflow is superseded: both synthetic nodes
remain available to permitted users through their assigned demo farm/sites.
`NODE_01` / `NODE_02`, the synthetic disclaimer, model/scaler contracts, charts,
3D visualization and 24/72/168-hour controls are preserved. Viewer users select
available saved results; Admin/Researcher users can run the three frozen models.
There are no GPS-based prediction offsets or new real-field claims.

## Backend and session compatibility

The existing FastAPI application attaches `local_only` and `research_access`
dependencies when registering the Yield and legacy Microclimate routers. Anonymous
requests receive 401, unauthorized roles 403, and missing/invalid CSRF on execution
403. Authorized JSON request/response contracts and prediction values are unchanged.
Existing `/api/c2/access/` farm and administration checks remain intact. The login
endpoint, minimal `/health` status, static assets and API schema/documentation are
not private data endpoints; the SPA application content is centrally guarded.

The original HttpOnly/SameSite=Strict session cookie formerly had path
`/api/c2/access`. `/me` now upgrades an existing valid cookie to `/api/c2`, deleting
the older path cookie while preserving its exact session token, database row and
absolute expiry. New logins use the wider path. Logout clears both paths and
revokes the stored session. No SQLite schema migration or account recreation occurs.
The existing 8-hour absolute / 30-minute inactivity limits are retained.

Access, Yield and Microclimate clients now share credentialed `sessionFetch`,
same-host API base selection, in-memory CSRF state and expiry notification. They
do not read the HttpOnly cookie or store tokens in localStorage. Stale request
responses cannot replace a newer login's CSRF value. Cookie `Secure=False` remains
intentional for the existing **loopback-only HTTP** setup; this is not a reviewed
internet-facing authentication deployment.

## Startup (existing accounts and database)

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From `frontend/`:

```powershell
npm run dev
```

Open **http://127.0.0.1:5173/login**. Consistently use `127.0.0.1` for frontend and
backend, or `localhost` for both. An explicit `VITE_API_BASE_URL` must use the same
hostname to preserve SameSite cookie behavior. Existing CORS origins remain the
two local port-5173 origins. The database remains
`%LOCALAPPDATA%/SmartAgricultureC2/access.sqlite3`, or the existing `C2_ACCESS_DB`
override. Do not change its path, delete it, or run account bootstrap again.

## Verification and limits

Executed commands:

```powershell
# backend/
.\.venv\Scripts\python.exe -B -m unittest app.c2.access.tests.test_access app.c2.microclimate.api.tests.test_api -v

# frontend/
npm run build
npm run test:c2
npm run test:microclimate:render
```

- **50 backend tests passed, 0 failed**: 26 access/security tests and 24 existing
  Microclimate/Yield API regressions, now using authenticated temporary accounts.
- **34 frontend tests passed, 0 failed**, including central guard decisions,
  navigation roles, safe destinations and case/encoding bypass checks.
- Production build passed without oversized-chunk warnings. Server rendering of
  the login form, access-denied state, role-dependent farm controls, Admin denial,
  existing page, nine charts and static farm fallback passed without React errors.
- Existing and farm-scoped predictions for all three models and both nodes match
  saved outputs exactly (maximum original-unit difference **0.0**). Yield remains
  275.59 g/plant for its existing regression example.
- Migration tests confirm an old-path cookie retains the same valid session and
  absolute expiry. Tests cover valid/invalid login, session refresh, logout,
  expiry/revocation, Viewer API denial, Researcher Admin denial and farm isolation.
- A real Uvicorn TCP check used the actual frontend API client, cookie/CSRF login,
  six model/node forecasts, Yield inference and CORS against an isolated temporary
  database with generated test-only credentials. No real Admin password was used.
- Browser tooling reports no available browser. Actual browser navigation,
  show/hide interaction, refresh/logout redirects, mobile visual layout and console
  behavior are **not newly browser-verified**. Markup, responsive CSS and pure guard
  logic tests are not substitutes for a manual browser smoke test.

The optional `npm run test:microclimate:live` now requires an authorized test
account supplied through `C2_TEST_USERNAME` / `C2_TEST_PASSWORD`; it never prints
credentials and signs out its own test session. Ordinary regression suites use
disposable databases, not your existing account store.

Files added: `frontend/src/auth/{AuthProvider,RequireAuth}.jsx`,
`frontend/src/auth/policy.js`, `frontend/src/pages/{Login,AccessDenied}.jsx`,
`frontend/src/styles/auth.css`, `frontend/tests/c2/authPolicy.test.mjs`, this guide.
Updated shared App/Navbar, farm components, API clients, regression scripts,
`backend/app/main.py`, and existing access routes/store helpers. No trained model,
scaler, dataset, experimental result or password-hashing algorithm was changed.
No packages were installed; no commits, pushes or deployment were performed.
