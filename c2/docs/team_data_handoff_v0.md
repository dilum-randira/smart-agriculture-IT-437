# C2 data handoff and parameter checklist (draft v0)

**Status:** proposal-derived working note, not an approved group-wide API or evidence of field validation.
**Scope:** predictive intelligence for Nai Miris; no individual student identifiers are included.

## Responsibilities and ownership

| Component | Owns | Provides |
| --- | --- | --- |
| C1 | Sensor collection, calibration, immutable raw data, anomaly flags, quality-aware processing | Timestamped, quality-labelled field measurements; crop and harvest logs where collected |
| C2 | Model-specific processing, forecasting, yield regression, evaluation and prediction uncertainty | 24h/72h/168h forecasts for soil moisture, air temperature and RH; next-7-day fresh yield kg/plot |
| C3 | ET0 / crop-water calculation, stress assessment, irrigation optimisation | Stage-aware schedule and water/risk trade-offs |
| C4 | Market forecasting, scenario decisions, explanations | Farmer-facing harvest guidance with assumptions and confidence |

The simple prediction references are **persistence** for the microclimate task and **training-set mean** for fresh yield. Learned comparisons are Attention-BiLSTM versus LSTM/GRU, and XGBoost versus Random Forest/SVR.

## C1 → C2 parameter matrix to confirm

| Variable | Expected units | Role | Validation requirement |
| --- | --- | --- | --- |
| Plot, timestamp, sensor and dataset version | Identifier / timezone-aware timestamp | Join/provenance | Consistent plot and issue-time boundaries |
| Soil moisture | Calibrated physical unit **to be confirmed** | Forecast input and target | Keep raw ADC and calibration details; never assume kPa = VWC |
| Air temperature | °C | Forecast input and target | Include quality flag and sensor metadata |
| Relative humidity | % | Forecast input and target | Physical range and time continuity checks |
| Soil temperature | °C | Optional covariate | Sensor calibration and sufficient coverage |
| Rainfall | mm per interval | Optional covariate | Aggregate as sums, distinguish zero from missing |
| Light intensity | lux | Optional covariate | BH1750 lux is not solar radiation W/m² |
| Planting, observed growth stage | Date, categorical event | Stage-aware covariate | Only stages known as of forecast issue |
| Completed irrigation events | Timing, measured amount/unit | Historical covariate | No future planned irrigation disguised as observed |
| Fresh harvest | kg per plot, dated and matched to crop cycle | Yield training target | Require genuine measured harvest and documented coverage |

**C3 water requirement dependency:** FAO Penman–Monteith ET0 may need radiation, wind and other meteorological data not supplied by C1's proposed sensor list. The team should audit trusted external weather sources rather than invent conversions.

**C4 data dependency:** historical Nai Miris prices and relevant units/markets must be verified, not assumed.

## C2 → downstream minimum output contract

Proposed keys: `prediction_id`, `plot_id`, `issued_at`, `target_start`, `target_end`, `variable`, `unit`, `median`, `lower`, `upper`, `interval_level`, `model_version`, `data_version`, `status`.

Consumers must distinguish valid, provisional, stale, and unavailable results. Missing intervals must be **null** rather than fabricated. Predictions require issue time, unit, model/data provenance and matching target horizon.

## PP1 readiness decisions

1. Agree a canonical soil-moisture measurement and calibration version with C1.
2. Confirm C1 sensor time zone, 15-minute cadence and hourly aggregation policy.
3. Agree an actual plot/cycle-based fresh-harvest record protocol with measured weights and coverage.
4. Check public datasets for crop identity, resolution, licensing, time coverage and soil-moisture availability.
5. Specify missing/stale data semantics before C3/C4 integrate predictions.
6. Agree shared technology and storage only after all members review requirements.
7. Verify whether the university's GitHub-to-Planner automation sees feature branches (not yet confirmed).

**Practice boundary:** Existing C2 code under `c2/practice/` uses synthetic examples for learning and contract tests. It is *not* field-data evidence, and is not an implementation of all four components.
