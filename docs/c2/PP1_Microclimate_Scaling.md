# C2 Step 3 ? executed train-only scaling evidence

**Synthetic Data — Prototype Evaluation Only**

Branch: `feature/c2-predictive-intelligence`. The scaling pipeline was actually
executed in `backend/.venv`; no neural-network training or package installation
occurred. New artifacts are under `backend/experiments/c2/microclimate/phase1_masked_scaled/`.

## Fitting policy

Separate StandardScaler-equivalent input and target parameters use population
variance (`ddof=0`). Shared across nodes, each unique `(node_id,timestamp)`
contributes once per role. Only original quality-eligible observations in the
frozen TRAIN partition and used by retained training histories/target windows
are fitted. INVALID/anomalous/supplied-imputed values and forward-filled
history values are excluded. No validation/test values or target labels
outside training can enter the fitting pool.

Input count: **11,724 per feature** (NODE_01: 5,865; NODE_02: 5,859),
Jan 1 00:00?Sep 6 11:00, 2025. Target count: **11,391 per feature**
(NODE_01: 5,698; NODE_02: 5,693), Jan 15 00:00?Sep 13 11:00, 2025.
Times are Asia/Colombo. Each fit CSV provides the actual unique source keys and
values. Shared parameters provide a consistent common-unit feature space;
node offsets remain represented rather than normalized away independently.

| Feature | Input mean | Input population std | Target mean | Target population std |
|---|---|---|---|---|
| soil_moisture_avg_index | 37.815685773 | 14.297337977 | 37.999393381 | 15.045079433 |
| air_temperature_c | 27.779749232 | 2.611512290 | 27.787227636 | 2.616794456 |
| relative_humidity_pct | 81.770787274 | 8.980247784 | 81.775765078 | 8.991267934 |

Full precision parameters, variances, scales and counts are in `scalers.json`.
Zero/numerically constant features use scale 1; std metadata remains measured.
No observations for a feature is an error. No scaling is fitted on flattened
sliding-window arrays or on masked target placeholders.

## Tensor verification

All saved X/y arrays are finite **float32**. Target masks remain boolean
`[N,168,3]`, historical masks boolean `[N,336]`. Counts below are unchanged
and apply equally to each target channel; historical counts are row positions.
They include repeats across overlapping windows and are not independent samples.

| Split | Node | X shape | y and target-mask shape | Valid targets/channel | History mask=True |
|---|---|---|---|---|---|
| train | NODE_01 | [5629, 336, 3] | [5629, 168, 3] | 929516 | 1859915 |
| train | NODE_02 | [5508, 336, 3] | [5508, 168, 3] | 909316 | 1816870 |
| validation | NODE_01 | [811, 336, 3] | [811, 168, 3] | 133648 | 267806 |
| validation | NODE_02 | [811, 336, 3] | [811, 168, 3] | 134726 | 269531 |
| test | NODE_01 | [811, 336, 3] | [811, 168, 3] | 134495 | 267351 |
| test | NODE_02 | [811, 336, 3] | [811, 168, 3] | 133368 | 267645 |

The original 336/168/3 contract, 160 valid target hours rule, samples, origins,
node isolation and frozen boundaries are preserved. Target mask=False cells
are saved as standardized **zero placeholders**; masks are mandatory for loss
and metrics. They are not fabricated target observations. Inverse actual-target
transforms emit NaN for those cells, preventing the training mean from being
misrepresented as a measured target.

## Inverse and metric reproduction

A fixed `1e-5` original-unit absolute tolerance (rtol=0) is enforced. Per-feature
maximum X inverse errors: `[1.7042777500364537e-06, 3.073895911143154e-07, 1.0316744720739734e-06]`. Eligible-y inverse errors:
`[1.7896538082595725e-06, 3.091342364314187e-07, 1.0193257438118053e-06]` (moisture INDEX, ?C, humidity percentage points respectively).

All **54 cumulative** and **3,024 lead-time** persistence metric rows reproduce
the original masked experiment within tolerance; their denominators are identical.
Maximum cumulative MAE/RMSE differences: `6.600649449239882e-08` /
`8.305138976538728e-08`. Maximum lead MAE/RMSE
differences: `1.7261692275560847e-07` /
`1.6727417451178894e-07`.

Persistence verification correctly bridges input-scaler inverse to target-space
predictions and target-scaler inverse. The two parameter sets are different and
must not be used interchangeably. Float32 quantization explains the small
nonzero differences; no physical-unit clipping or model change occurred.

## Tests and preservation

**54 tests passed, 0 failures, 0 errors, 0 skipped.**
This includes the previous 37 and 17 new scaling tests. Tests verify direct
StandardScaler equivalence, masked-value exclusion, validation/test poisoning
invariance, duplicated-origin invariance, zero-variance safeguards, feature order,
serialization, finite dtypes/shapes, masks, inverse transforms, original-unit
metrics, node/time alignment and original-artifact preservation.

The CSV plus all previous complete-case and masked artifacts were unchanged:
**39 protected files**, SHA-256 checked before/after.
The copied sample manifest is byte-identical to the unscaled masked manifest.
Only new code/documentation and the new scaled experiment directory were created.

## Files and reproduction

Added: `scaling.py`, `run_phase1_scaled.py`, `test_scaling.py`,
`README_scaled.md` under `backend/app/c2/microclimate/`, plus this document.
No existing source file was modified by this step.

From repository root (PowerShell):

```powershell
Push-Location backend
try {
    .\.venv\Scripts\python.exe -B -m app.c2.microclimate.preprocessing.run_phase1_scaled
    .\.venv\Scripts\python.exe -B -m unittest app.c2.microclimate.preprocessing.tests.test_phase1 app.c2.microclimate.preprocessing.tests.test_phase1_masked app.c2.microclimate.preprocessing.tests.test_scaling -v
} finally {
    Pop-Location
}
```

The earlier artifacts must exist; this command never reruns/overwrites those
experiments. Fit parameters and row pools, six NPZs, original-unit metrics,
metric comparison, origin manifest, reports and test logs are saved in the
new directory. Every experimental output has the synthetic disclaimer.

## Remaining limits

No preprocessing scaling blocker remains for these saved tensors. Correct
framework-specific batching and differentiable mask-aware loss still require
verification when Phase 2 starts. No LSTM/GRU/Attention BiLSTM is implemented,
trained or tuned. NASA POWER/ERA5-Land, real C1 measurements, growth-stage
labels and sensor calibration are not introduced. Quality provenance, stale
historical fills, informative missingness, overlap dependence and synthetic-only
accuracy limitations remain. No real Nai Miris field performance is established.
