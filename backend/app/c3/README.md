# C3 — Adaptive Multi-Objective Irrigation Optimisation Engine

Owner: Gayantha W.M.K (IT23317826)

**Status: all 12 stages have working, tested code. Everything runs on
SYNTHETIC data and placeholder/proxy crop and soil values until field data
and the open questions below are resolved. Nothing here is a research
result.**

## Run (from the `backend/` folder, with the virtual environment active)

```bash
python -m pip install -r requirements-c3.txt
python -m app.c3.check_setup
python -m pytest tests/c3
python -m app.c3.scripts.run_synthetic_evaluation   # season comparison (synthetic)
python -m app.c3.scripts.tune_nsga2                 # NSGA-II tuning (synthetic)
python -m app.c3.scripts.run_real_weather_evaluation  # real weather + past forecasts (demo location)
fastapi dev app/main.py                             # API; C3 endpoints under /c3
```

Dashboard: `cd frontend && npm install && npm run dev`, then open
http://localhost:5173/irrigation (needs the API running).

## Code map

| File | Stage | What it does |
| --- | --- | --- |
| data_loading.py | 2 | Load and check input files; spike check |
| et0.py | 3 | FAO-56 Penman-Monteith ET0 (Eq. 17 or 19), wind height (Eq. 47) |
| water_balance.py | 4 | Kc curve, ETc, TAW/RAW, Ks, daily root-zone balance |
| growth_stages.py | 5 | FAO-56 growth stages; per-stage settings |
| stress_classifier.py | 6, 8 | Random Forest stress classifier; reactive ML baseline |
| climate_risk.py | 7 | Heat, drought, waterlogging, root-rot flags |
| baselines.py | 5, 8 | Fixed threshold, DoA, stage-aware rules; season simulator |
| optimiser.py | 9 | NSGA-II plan (4 objectives), partial refills |
| cost.py | 9 | Irrigation cost (LKR) from water and events |
| weather_sources.py | 10 | Open-Meteo forecast / ERA5 history; C2 prediction format |
| planner.py | 10 | Today's recommendation from soil reading + forecast |
| evaluation.py | 11 | Season comparison of all schedules |
| api.py | 12 | FastAPI router (/c3/status, /c3/et0, /c3/plan, /c3/demo/...) |
| frontend/src/pages/c3/IrrigationPlanning.jsx | 12 | Irrigation Operations Dashboard |

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
   normal at vegetative and fruiting stages) — code ✅: per-stage trigger
   and partial-refill settings (baselines.stage_aware_rule, optimiser
   refill_fraction). Evidence: Jeeatid et al. (2018) Food Chemistry
   245:792-797 — water stress after anthesis raised capsaicinoid
   concentration but reduced yield; capsaicinoid yield rose only in some
   C. chinense cultivars. Stage lengths and deficit levels still needed.
6. Water stress probability classifier (XGBoost / Random Forest) — code ✅
   (Random Forest, scikit-learn). Interim label: FAO-56 Ks < 1 tomorrow
   without irrigation (agreed by the student; confirm with supervisor).
   On simulated data it partly re-learns FAO-56, so scores are not accuracy.
7. Climate risk assessment (heatwave, drought, waterlogging, root rot) —
   daily risk flags ✅ (heat: Tmax >= 33 degC, Erickson & Markhart 2002;
   drought: Ks < 1, FAO-56; root rot: water beyond FC and Tmean 23.9-33.3
   degC, UC IPM; waterlogging: longest wet run only, threshold not yet
   confirmed). Root-rot risk days are an NSGA-II objective.
8. Baseline schedules: fixed threshold ✅, DoA Sri Lanka interval
   schedule ✅, generic reactive ML ✅ (Random Forest; align with the
   "Paper 8" methodology once that paper is identified)
9. NSGA-II optimisation with pymoo (yield, water-use efficiency,
   water volume, cost, climate risk) — version 2 ✅: decides WHICH days to
   irrigate; each irrigation refills to field capacity (FAO-56 Example 38).
   Objectives: water, relative ET deficit (FAO-33 yield proxy, worst
   weather scenario), irrigation events, root-rot risk days. Minimum
   practical amount is a setting (off until sourced). NSGA-II pop 60 x 80
   generations, tuned with `python -m app.c3.scripts.tune_nsga2` (finds the
   exact Pareto front in all 120 synthetic test cases). Cost (cost.py) is
   reported, not a separate objective: water and events are already
   objectives, so every cost trade-off is on the Pareto front.
10. Adaptive 7-day schedule that updates when new sensor data or C2
    forecasts arrive — code ✅: planner.plan_today (soil reading ->
    depletion, forecast -> 7-day plan); weather_sources.py fetches
    Open-Meteo forecasts / ERA5 history and parses C2's proposed format.
    Cross-check on real ERA5 weather (May 2025, placeholder location
    7.9N 80.7E): our ET0 tracks Open-Meteo's FAO ET0 (r = 0.96) but is
    0.46 mm/day higher on average; cause not yet investigated.
11. Evaluation against the baselines — pipeline ✅ and first run on
    SYNTHETIC data (`python -m app.c3.scripts.run_synthetic_evaluation`).
    Not a result. On synthetic data NSGA-II (deficit 0) uses about the
    same water as the fixed threshold and the reactive ML baseline (all
    ~449-455 mm, zero stress); DoA uses less water but has 27-35 stress
    days. With perfect knowledge of soil water and synthetic weather, a
    forecast-based optimiser has little room to help; its value must be
    tested on real forecasts and sensor data. Assumptions: season starts
    at field capacity; schedules know the true depletion.
    REAL-WEATHER test (`python -m app.c3.scripts.run_real_weather_evaluation`):
    Yala 2025 (90 days from 1 May) at the demo location Mahailuppallama,
    real ERA5 weather and real past forecasts (Open-Meteo Previous Runs);
    soil/crop still placeholders/proxy. With PERFECT forecasts NSGA-II
    beats the reactive rules (421 vs 434-444 mm, drainage 5.6 vs 12.5-18.8
    mm, root-rot days 1 vs 3). With REAL forecasts the advantage disappears
    (about 441 mm, drainage 14.7 mm). Run-to-run sensitivity of the
    optimiser is about +/-10 mm per season, so 2-4 % differences are not
    meaningful; one location and one season only. Interpretation: forecast
    quality limits the benefit, which links C3 to C2's forecasts.
    "Trust the forecast" (worst_case_no_rain=False) did not clearly help,
    so the "rain fails" safety case stays the default.
12. FastAPI endpoints for C4 and the Irrigation Operations Dashboard
    (weekly schedule, water-use optimisation, risk alerts) — code ✅:
    api.py router mounted in backend/app/main.py; dashboard page at
    /irrigation (frontend/src/pages/c3/). Live demo mode
    (/c3/demo/live-plan) uses today's real forecast at the demo location
    and shows, per day, the facts behind the plan and what reactive rules
    would do instead. Synthetic mode stays available. All demo outputs are
    labelled with their data source and placeholders.

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
