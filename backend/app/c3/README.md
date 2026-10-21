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
7. Climate risk assessment (heatwave, drought, waterlogging, root rot) —
   daily risk flags ✅ (heat: Tmax >= 33 degC, Erickson & Markhart 2002;
   drought: Ks < 1, FAO-56; root rot: water beyond FC and Tmean 23.9-33.3
   degC, UC IPM; waterlogging: longest wet run only, threshold not yet
   confirmed). Not yet used as an NSGA-II objective.
8. Baseline schedules: fixed threshold ✅ and DoA Sri Lanka interval
   schedule ✅ (code done); reactive ML ("Paper 8" methodology) still to do
9. NSGA-II optimisation with pymoo (yield, water-use efficiency,
   water volume, cost, climate risk) — version 2 ✅: decides WHICH days to
   irrigate; each irrigation refills to field capacity (FAO-56 Example 38).
   Objectives: water, relative ET deficit (FAO-33 yield proxy, worst
   weather scenario), irrigation events, root-rot risk days. Minimum
   practical amount is a setting (off until sourced). NSGA-II pop 60 x 80
   generations, tuned with `python -m app.c3.scripts.tune_nsga2` (finds the
   exact Pareto front in all 120 synthetic test cases). Still to add: cost
   (needs water price), partial refills for deficit irrigation (Stage 5).
10. Adaptive 7-day schedule that updates when new sensor data or C2
    forecasts arrive
11. Evaluation against the baselines — pipeline ✅ and first run on
    SYNTHETIC data (`python -m app.c3.scripts.run_synthetic_evaluation`).
    Not a result. With optimiser v2 the tiny daily irrigations are gone,
    but on synthetic data it is only slightly better than the fixed
    threshold (about 1 % less water at zero stress, with more irrigation
    events). Assumptions: season starts at field capacity; optimiser knows
    the true depletion.
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
- Waterlogging threshold: "more than 2 days at flowering causes total
  yield loss" (Abdulrasaq & Arslan, 2026, Russ. J. Plant Physiol. 73(2):51)
  is still NOT confirmed from the paper itself (paywalled; only search
  summaries say it). The companion paper (Abdulrasaq, Kiremit & Arslan,
  2026, Anadolu J. Agric. Sci. 41) reports a 6-day threshold across all
  stages. Get the full text via the library.
- Kc for C. chinense: Raphael et al. (2018), Agricultural Water Management,
  pp. 179-185, measured Kc for Capsicum chinense in Nigeria (initial
  0.32-0.7, mid 1.02-1.45, late 0.76-0.9). Better than the bell pepper
  proxy if Nai Miris is C. chinense; needs the full paper for stage
  lengths and single values.
- Soil FC/WP: the open 3D soil database for Sri Lanka (PMC7648115) maps
  water content at 0.33 bar and 15 bar by depth; take values for the test
  plot's location once it is known.
- C2 interface: C2's handoff note (feature/c2-ml-foundation,
  c2/docs/team_data_handoff_v0.md) says C2 forecasts soil moisture, air
  temperature and RH only, in a long format (variable, median, lower,
  upper). Rain, wind and radiation for ET0 must come from an external
  weather forecast; the synthetic C2 file assumed C2 provides them.
- Heat threshold (33 degC) comes from a constant-temperature study and is
  compared here with daily Tmax; a heat-stress source using daily maximum
  temperature would be better.
- The model of C1's soil moisture sensor, so its datasheet measuring range
  can be used as the validity limit (ask the C1 member). A sudden-jump
  check will be added later. Still not in the repo; C2's handoff note also
  says the soil moisture unit is "to be confirmed" (kPa tension or
  volumetric water content), which matters for the water balance.
- Minimum practical irrigation amount for the plot's irrigation method
  (currently off).
