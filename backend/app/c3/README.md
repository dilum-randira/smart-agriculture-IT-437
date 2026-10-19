# C3 — Adaptive Multi-Objective Irrigation Optimisation Engine

Owner: Gayantha W.M.K (IT23317826)

**Status: Stage 1 (setup) only. No model, calculation or schedule in this
folder has been validated. Nothing here is a research result.**

## Run (from the `backend/` folder, with the virtual environment active)

```bash
python -m pip install -r requirements-c3.txt
python -m app.c3.check_setup
python -m pytest tests/c3
```

## Stages

1. Setup and folder structure  ← current
2. Input data format, sample data, loading and validation
3. Reference evapotranspiration (FAO-56 Penman–Monteith)
4. Crop coefficients, crop water need and 7-day soil water balance
5. Baseline schedules (fixed threshold, DoA recommendation)
6. NSGA-II optimisation with pymoo
7. Evaluation against baselines
8. FastAPI endpoints for C4 and the dashboard
