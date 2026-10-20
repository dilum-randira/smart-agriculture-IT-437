# C2 yield workspace

The shared `/predictions` route renders `YieldPrediction.jsx`. Shared navigation,
other component routes, and the existing C4 HTML demo are preserved.

## Run

From `frontend/`: `npm install` (if needed), then `npm run dev`.
Open `http://localhost:5173/predictions`.

From `backend/`, with the existing Python environment activated:
`python -m uvicorn app.main:app --reload --port 8000`.
The existing environment must contain the trained model's dependencies, including
XGBoost and joblib. No backend requirements or model files are changed here.

The C2 service defaults to `http://127.0.0.1:8000`. The Vite project root is
`frontend/src/`, so put `VITE_API_BASE_URL=http://127.0.0.1:8000` in
`frontend/src/.env.local` when overriding it, or set the environment variable
before starting Vite. Restart Vite after changes. This value is a public API URL,
never a secret. Backend CORS currently allows localhost/127.0.0.1 on port 5173.

## Research data

`assets/c2/` contains the original SVG and two aggregate CSV snapshots, with
provenance documented in its README. The UI does not import backend datasets
or trained models. The benchmark selector changes the displayed metric, not the
prediction model. The API always selects its existing tuned XGBoost model.

SHAP values are global development-set explanations. Predicted values are
experimental trait-based estimates with an unverified fresh/dry basis.
The result clears when measurements change, preventing stale output from being
associated with new inputs. Reset cancels in-flight work. Requests time out after
30 seconds. The frontend accepts fractional nonnegative traits and strictly
positive flowering days, matching the current Pydantic schema.

## Checks

- `npm run build`
- `npm run test:c2`

The Node tests isolate transport failures, cancellation, timeout, API validation,
numeric boundaries, and malformed response handling using test-only fixtures.
They do not substitute for a live backend test.

Manual browser checks: submit measured values, check the submitted summary,
edit and reset, select MAE/RMSE/R², expand source tables, navigate all shared
routes, and check phone/tablet widths and reduced-motion mode. Screen-reader
wording should also receive a human review.

## Implementation inventory

Created:

- `pages/c2/YieldPrediction.jsx` and this README
- `components/c2/YieldHero.jsx`
- `components/c2/YieldPredictionForm.jsx`
- `components/c2/YieldPredictionResult.jsx`
- `components/c2/YieldModelComparison.jsx`
- `components/c2/YieldExplainability.jsx`
- `components/c2/YieldIcon.jsx`
- `services/c2/yieldApi.js` and `yieldResearch.js`
- `styles/c2/yieldPrediction.css`
- `assets/c2/nai-miris-plant.svg`, both aggregate CSVs, and provenance README
- `frontend/tests/c2/yieldApi.test.mjs` and `VERIFICATION.md`

Updated: `App.jsx` for the route, `Navbar.jsx` for brand-link accessible naming
and text contrast, `pages/README.md`, `frontend/README.md`, and `package.json`
for the test command. No application dependencies were added.
