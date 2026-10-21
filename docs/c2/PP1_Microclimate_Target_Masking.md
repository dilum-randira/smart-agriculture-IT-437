# C2 Phase 1 target masking ? executed results

**Synthetic Data — Prototype Evaluation Only**

The old all-168-labels-valid rule rejected every validation NODE_01 and test
NODE_02 forecast. The corrected version retains windows with at least 160/168
usable hours per target and scores only original observations with mask=True.
It preserves the original chronology and raw targets; no target is invented,
filled or interpolated. All original Phase 1 artifacts and the CSV match the
SHA-256 preservation manifest.

## Policy and development evidence

The target mask is boolean `[N,168,3]`, derived before historical filling:
`NOT (INVALID OR is_anomaly OR is_imputed)`, repeated across all three channels.
Unflagged WARN is eligible. Even single-sensor supplied imputation conservatively
invalidates the whole row. This does not establish real measurement provenance.

Training-only target quality had median 165 valid hours at both nodes, minima
161 (NODE_01) and 157 (NODE_02). A fixed >=95% floor requires ceil(.95*168)=160
valid hours per target, excluding 121 lower-coverage NODE_02 training windows.
This operational rule was fixed before validation/test evaluation, without
using model errors. No empty-label window is accepted. Inputs must remain finite.

## Coverage

Counts below are **per target**; all three targets have identical masks. Counts
include repeated forecast/target pairs from overlapping origins. Unique target
timestamps are shown separately and are not multiplied by three.

| Split | Node | Samples | Rejected | Valid 1?24h | Valid 1?72h | Valid 1?168h | Unique valid target times |
|---|---|---|---|---|---|---|---|
| train | NODE_01 | 5629 | 0 | 132782 | 398338 | 929516 | 5698 |
| train | NODE_02 | 5508 | 121 | 129923 | 389735 | 909316 | 5693 |
| validation | NODE_01 | 811 | 0 | 19104 | 57312 | 133648 | 960 |
| validation | NODE_02 | 811 | 0 | 19211 | 57691 | 134726 | 966 |
| test | NODE_01 | 811 | 0 | 19190 | 57590 | 134495 | 966 |
| test | NODE_02 | 811 | 0 | 19076 | 57164 | 133368 | 959 |

Every input is `[N,336,3]`; raw target and boolean target mask are both
`[N,168,3]`. Original historical observation masks remain `[N,336]`.

## Persistence masked MAE / RMSE

Moisture uses index units, not calibrated VWC. Temperature errors use ?C;
humidity errors use percentage points. Each denominator is the actual valid
observation count above. Zero eligible observations yields unavailable metrics.

| Split | Node | Target | 1?24h | 1?72h | 1?168h |
|---|---|---|---|---|---|
| train | NODE_01 | soil_moisture_avg_index | 1.372 / 1.837 | 2.178 / 2.862 | 3.277 / 4.362 |
| train | NODE_01 | air_temperature_c | 2.934 / 3.608 | 2.937 / 3.610 | 2.939 / 3.611 |
| train | NODE_01 | relative_humidity_pct | 10.249 / 12.603 | 10.265 / 12.612 | 10.274 / 12.617 |
| train | NODE_02 | soil_moisture_avg_index | 1.379 / 1.861 | 2.179 / 2.864 | 3.263 / 4.368 |
| train | NODE_02 | air_temperature_c | 2.933 / 3.608 | 2.937 / 3.610 | 2.938 / 3.611 |
| train | NODE_02 | relative_humidity_pct | 10.220 / 12.559 | 10.232 / 12.566 | 10.239 / 12.569 |
| validation | NODE_01 | soil_moisture_avg_index | 1.349 / 1.719 | 1.965 / 2.459 | 2.430 / 3.104 |
| validation | NODE_01 | air_temperature_c | 2.966 / 3.647 | 2.966 / 3.643 | 2.965 / 3.641 |
| validation | NODE_01 | relative_humidity_pct | 10.352 / 12.744 | 10.376 / 12.751 | 10.380 / 12.757 |
| validation | NODE_02 | soil_moisture_avg_index | 1.365 / 1.755 | 1.916 / 2.390 | 2.360 / 3.057 |
| validation | NODE_02 | air_temperature_c | 2.940 / 3.613 | 2.940 / 3.611 | 2.940 / 3.611 |
| validation | NODE_02 | relative_humidity_pct | 10.245 / 12.588 | 10.274 / 12.603 | 10.288 / 12.620 |
| test | NODE_01 | soil_moisture_avg_index | 1.392 / 1.803 | 1.974 / 2.535 | 2.701 / 3.394 |
| test | NODE_01 | air_temperature_c | 2.925 / 3.596 | 2.928 / 3.596 | 2.930 / 3.597 |
| test | NODE_01 | relative_humidity_pct | 10.233 / 12.590 | 10.233 / 12.571 | 10.221 / 12.550 |
| test | NODE_02 | soil_moisture_avg_index | 1.471 / 1.905 | 2.080 / 2.674 | 2.767 / 3.579 |
| test | NODE_02 | air_temperature_c | 2.903 / 3.568 | 2.901 / 3.564 | 2.903 / 3.564 |
| test | NODE_02 | relative_humidity_pct | 10.128 / 12.441 | 10.124 / 12.423 | 10.107 / 12.397 |

## Evidence, tests and reproduction

Executed pipeline: `python -B -m app.c2.microclimate.preprocessing.run_phase1_masked` from
`backend/`, using `backend/.venv/Scripts/python.exe`.

Executed tests: **37 passed, 0 failed, 0 errors, 0 skipped** (20 original + 17 new).
Saved metrics are independently recomputed from the NPZs in integration tests.

From the repository root in PowerShell:

```powershell
Push-Location backend
try {
    .\.venv\Scripts\python.exe -B -m app.c2.microclimate.preprocessing.run_phase1_masked
    .\.venv\Scripts\python.exe -B -m unittest app.c2.microclimate.preprocessing.tests.test_phase1 app.c2.microclimate.preprocessing.tests.test_phase1_masked -v
} finally {
    Pop-Location
}
```

Outputs: `backend/experiments/c2/microclimate/phase1_masked/`: six NPZs,
six actual-versus-persistence plots, lead-error plot, cumulative/lead metrics,
origin manifest, development quality analysis, validation report, preservation
manifest, summary and test record. Plot targets have gaps at masked positions.
Each output carries the synthetic evaluation disclaimer.

Modified code: `pipeline.py` adds masked windows, scores and NumPy reference
loss, preserving the complete-case API; `run_phase1.py` accepts an optional
plot mask. Added `run_phase1_masked.py`, `test_phase1_masked.py` and
`README_masked.md`; the original README links the corrected version.

## Remaining limitations

Masks are mandatory for downstream training; saved y includes untrusted raw
values where the mask is False. A tested NumPy reference MAE/MSE loss exists,
but framework-specific differentiable loss integration remains Phase 2.
Neither target masks nor future observations may enter model inputs.

No scaling, neural networks, training, tuning or external dataset integration
is implemented in this step. Frozen split boundaries are unchanged. Missingness
may be informative, historical fills may be stale, and overlapping counts are
not independent. The threshold is an explicit policy, not a proven optimum.
Changed evaluation cohorts prevent interpreting differences from complete-case
metrics as model improvement. These synthetic results demonstrate no real
Nai Miris field accuracy. Yield Prediction and C1/C3/C4 are untouched.
