# C2 verification — 20 October 2026

The user flow tested was: `/predictions` → enter five measured traits →
POST to the existing FastAPI model → render the actual response with research
limitations and submitted measurements.

## Passed

- Production Vite build and `git diff --check`.
- Eight Node service tests (`npm run test:c2`).
- Real API HTTP 200 for example inputs 65, 5, 10, 5, 80, returning
  **489.18 g/plant**, Tuned XGBoost, and the expected research metadata.
  This is a test request, not a measured field observation or hardcoded UI value.
- Headless Chromium browser submission displayed the live API result.
- Empty-field validation, focus on first invalid field, input editing, and
  removal of stale results.
- Loading and disabled submit state, cancellation, reset, network failure,
  and successful retry. Network failure was intentionally intercepted only
  in the test browser; successful predictions used the real backend.
- MAE/RMSE/R² switching, negative R² rendering, and expanded benchmark table.
- Shared Overview, Monitoring, Irrigation, Harvest, and not-found routes.
- Mobile menu navigation and closing after selection.
- No horizontal overflow at 320, 390, 768, and 1440 CSS pixels.
- Reduced-motion CSS disables animation and smooth scrolling.
- Zero browser page errors during the flow.
- Final axe accessibility scans: zero violations at 1440 and 390 pixels.
- Desktop and mobile screenshots visually inspected.
- Aggregate CSV snapshots match their backend sources by SHA-256.

Playwright and axe were installed only in a temporary directory outside the
repository for browser QA. They are not application dependencies. The existing
backend server on port 8000 was used and left running. The frontend QA server
was stopped after verification.

## Remaining limits

Automated accessibility checks do not replace human screen-reader testing.
Browsers other than Chromium and physical mobile devices were not tested.
The benchmark and SHAP files are static snapshots and need an explicit refresh
when reviewed experiments change. Scientific limitations remain visible in the
interface: aggregate training data, unverified fresh/dry yield basis, limited
preliminary test performance, and no Sri Lankan field-level validation.
