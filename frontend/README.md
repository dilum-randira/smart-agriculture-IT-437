# React + Vite + JavaScript (JSX) frontend

## C2 integration update

`/predictions` now opens the C2 Yield Prediction workspace connected to the
existing FastAPI endpoint. Other research routes and the earlier C4 demo remain
as described below. See [C2 setup and file inventory](src/pages/c2/README.md)
and [verification results](tests/c2/VERIFICATION.md). Run `npm run test:c2`
for API service tests. No new application dependencies were added.

The scaffold notes below describe the original shared shell; C2 now has its
own implementation under the functional `src/*/c2/` folders.

The **new shared application** uses React, Vite, JavaScript (JSX) and Tailwind CSS. No TypeScript setup is required.

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally http://localhost:5173).
Build with `npm run build` (output: `frontend/dist/`).

## Why is the Vite entry at src/index.html?

The existing files `frontend/index.html`, `frontend/app.js` and
`frontend/style.css` contain **another member's earlier C4 HTML/JS demo**.
They have been deliberately kept unchanged to avoid discarding work.
Vite is configured with `root: frontend/src/`, so its own React
`src/index.html` is the new application's entry point.

The earlier C4 demo is **not yet migrated to React**, and its API/static-asset
paths are not part of this Vite shell. The C4 owner should decide how to
migrate or reuse it before the group removes or edits those files.

## Ownership and routes

Future pages belong under `src/pages/c1/` through `src/pages/c4/`.
Each owner creates actual page code. This scaffold intentionally adds
no files inside individual C1–C4 directories and no nonfunctional routes.

## Shared navigation (current)

The common React application now provides a responsive top navigation bar,
working client-side routes, and an Overview page with a **real** connection
check against the FastAPI `GET /health` endpoint.

| URL | Workspace |
| --- | --- |
| `/` | Overview and backend health status |
| `/monitoring` | Field Monitoring |
| `/predictions` | Predictions |
| `/irrigation` | Irrigation Planning |
| `/harvest` | Harvest & Market |

These workspace routes are **not** finished component pages and do not
present synthetic readings as real results. When members implement their
pages under `src/pages/`, shared routing will be updated to mount them.
There are no added files inside individual component folders.

To check the backend status, start the FastAPI server on port 8000.
The default frontend base URL is `http://localhost:8000`, or set
`VITE_API_BASE_URL` in a local Vite environment file if needed.
The health check only confirms that the shared API is responding; it does
not verify model or sensor availability.

## Shared Navbar implementation

The common responsive top navigation is implemented in `src/components/Navbar.jsx`.
It uses the existing React Router routes in `src/App.jsx`. On narrow screens,
a Menu button exposes the links; the active route is highlighted, and the menu
closes after navigation. The button exposes its expanded state to assistive technology.

Members can develop their own pages later without editing the shared Navbar.
The current route workspaces are honest integration-status views, not real field-data results.
