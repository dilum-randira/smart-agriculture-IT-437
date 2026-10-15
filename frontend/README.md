# React + Vite + TypeScript frontend

The **new shared application** is React, Vite and Tailwind CSS.

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
