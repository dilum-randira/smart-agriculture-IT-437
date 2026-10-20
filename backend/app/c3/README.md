# C3 — Adaptive Multi-Objective Irrigation Optimisation Engine

Owner: Gayantha W.M.K (IT23317826)

**Status: Stage 2 in progress. All data in c3_data/sample is synthetic.
No model, calculation or schedule in this folder has been validated.
Nothing here is a research result.**

## Run (from the `backend/` folder, with the virtual environment active)

```bash
python -m pip install -r requirements-c3.txt
python -m app.c3.check_setup
python -m pytest tests/c3
```

## Stages

These follow the C3 tasks in the approved Topic Assessment Form (26-IT-437).

1. Setup and folder structure  ✅ done
2. Input data: synthetic sample data ✅ done; loading and validation ✅ done
   (soil moisture sensor limit still waits for C1's sensor model)
3. Reference evapotranspiration (FAO-56 Penman–Monteith) ✅ done, tested
   against FAO-56 Examples 2, 3, 8 and 18
4. Crop water need (Capsicum Kc) and 7-day soil water balance ✅ code done,
   tested against FAO-56 Examples 28, 36 and 37 (real Kc ini, stage
   lengths and soil values still needed)
5. Stage-aware irrigation rules (deficit irrigation at flowering,
   normal at vegetative and fruiting stages)
6. Water stress probability classifier (XGBoost / Random Forest)
7. Climate risk assessment (heatwave, drought, waterlogging, root rot)
8. Baseline schedules: fixed threshold ✅ and DoA Sri Lanka interval
   schedule ✅ (code done); reactive ML ("Paper 8" methodology) still to do
9. NSGA-II optimisation with pymoo (yield, water-use efficiency,
   water volume, cost, climate risk)
10. Adaptive 7-day schedule that updates when new sensor data or C2
    forecasts arrive
11. Evaluation against the baselines
12. FastAPI endpoints for C4 and the Irrigation Operations Dashboard
    (weekly schedule, water-use optimisation, risk alerts)

## Open questions (data sources)

The supervisor and the screening panel both asked the team to check data
availability. For C3 these are still open:

- Crop: confirm Nai Miris with the supervisor, and whether it is
  *Capsicum annuum* (as the form says) or *C. chinense*.
- Kc ini and crop stage lengths for the crop (currently only an FAO-56
  bell pepper proxy for Kc mid/end, root depth and p).
- Yield response to water, needed for the yield objective.
- A citation showing deficit irrigation at flowering raises capsaicin.
- Labels ("stressed" / "not stressed") to train the water stress classifier.
- DoA chilli schedule: HORDI gives intervals (4-5 days early, weekly later)
  but not the day "early" ends or the amount per irrigation. The code
  currently assumes each irrigation refills the root zone; both points
  need a source or must be stated as assumptions in the thesis.
- Water cost (LKR/m3) for the test plot.
- Which paper "Paper 8" is, for the reactive ML baseline.
- The model of C1's soil moisture sensor, so its datasheet measuring range
  can be used as the validity limit (ask the C1 member). A sudden-jump
  check will be added later.
