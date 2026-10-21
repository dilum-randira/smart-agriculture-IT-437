# C2 microclimate forecasting — Phase 1

For the corrected target-masked version, see [README_masked.md](README_masked.md).
This document describes the preserved original complete-case experiment.

**Synthetic Data — Prototype Evaluation Only**

This implements the proposal specification supplied for PP1: 336 historical
hours to 168 consecutive future hours, in the fixed target order
`soil_moisture_avg_index`, `air_temperature_c`, `relative_humidity_pct`.
Soil moisture is an **index, not calibrated volumetric water content**.
There is no real C1 integration, field-accuracy claim or model training here.

## Reproduce

From the repository root in PowerShell:

```powershell
Push-Location backend
try {
    .\.venv\Scripts\python.exe -B -m app.c2.microclimate.preprocessing.run_phase1
    .\.venv\Scripts\python.exe -B -m unittest app.c2.microclimate.preprocessing.tests.test_phase1 -v
} finally {
    Pop-Location
}
```

Uses only existing NumPy, pandas, Matplotlib and the standard library. No
installation, training, network access or API integration is required. The
runner rewrites its own generated evidence under
`backend/experiments/c2/microclimate/phase1/`; it never writes the input CSV,
yield artifacts or other components. `--help` describes configurable lookback,
horizon, stride and split fractions. Defaults are 336/168, hourly stride and
70%/15%/15%. Use the defaults for the submitted PP1 methodology. Alternate runs
should use `--output` pointing to a separate C2 experiment directory.

## Validation and quality policy

The exact 23-column schema is required. Numeric values must be finite; required
fields cannot be missing. Booleans, identifiers, timezone-aware whole-hour
timestamps, duplicate keys, node/zone consistency, hourly continuity, allowed
statuses, synthetic origin, quality-score and humidity ranges, nonnegative
physical fields, and imputation flag/field consistency are checked. Missing
`imputed_fields` is permitted only for records not flagged imputed. The
runner also checks the supplied dataset has 17,520 rows and the two expected
nodes. It records every column's missingness and all quality counts.

Rows are **never deleted before defining time boundaries**. INVALID rows,
anomalies and supplied imputed rows are unusable observations. Their three
historical target values are masked and forward-filled from earlier valid
values in the **same node and partition**. No backward fill, interpolation,
training-derived statistic or validation/test fit occurs. Leading unknown
history remains unknown, so affected windows are rejected. The saved
`history_valid_mask` identifies the original usable observations; long fills
may be stale, and their duration is not evidence of data freshness.

WARN rows are retained only if neither anomalous nor imputed. No undocumented
quality-score threshold is invented. All 168 target steps must be usable;
target labels are never filled. Supplied imputations are excluded because
their causal provenance is unavailable. The whole row is conservatively
masked, including when only one underlying moisture sensor was imputed.

This strict policy leaves **zero NODE_01 validation windows and zero NODE_02
test windows**. Those metrics are blank/NaN with count zero, never zero error.
Plots for empty cohorts are not fabricated. This is an evaluation coverage
blocker, not evidence that a model fails or succeeds. Before Phase 2, review
quality provenance and the policy with the supervisor; do not move splits
after inspecting test scores. The pipeline is complete but two-node held-out
performance is not established.

## Splits, tensors and leakage

One common calendar is split before quality filtering/window generation.
All input and output timestamps stay inside the same partition and node;
validation/test do not borrow training history. This intentionally sacrifices
the first 336 hours of each partition. No target horizon crosses a boundary.
Default cutoffs in Asia/Colombo (UTC+05:30) are:

| Split | Inclusive start | Inclusive end | Hours/node |
|---|---|---|---:|
| Training | 2025-01-01 00:00 | 2025-09-13 11:00 | 6,132 |
| Validation | 2025-09-13 12:00 | 2025-11-07 05:00 | 1,314 |
| Held-out test | 2025-11-07 06:00 | 2025-12-31 23:00 | 1,314 |

Every NPZ has `X: [N,336,3]`, `y: [N,168,3]`, a boolean historical
observation mask, target/feature names, timezone and forecast origins as UTC
Unix nanoseconds. Reconstruct target times as `origin + 1..168 hours`; input
times are `origin - 335..0 hours`. Load with `np.load(..., allow_pickle=False)`.
The sample CSV records these endpoints explicitly. All tensors are finite;
empty cohorts retain their full rank with N=0. NPZs are raw-unit inputs, not
normalized. Phase 2 must fit any scaler **only on the training partition**.

Only the three historical core targets are active features in this phase.
Forecast-weather fields and unverified derived covariates are not inputs.
Unavailable growth stage, planting date and crop age remain in the documented
future feature contract and are not invented or silently encoded. NASA POWER
and ERA5-Land are not loaded or joined.

## Persistence and evidence

Persistence repeats each feature's last valid historical value for all future
168 hours. Cumulative MAE/RMSE use leads **1–24, 1–72, 1–168**, not disjoint
bands. Each node/target/split has sample counts and `samples × hours` scored
values. Rolling hourly origins overlap; these are not independent samples or
confidence intervals. Lead-time CSVs score each of the 168 leads separately.
No aggregate across targets with incompatible units is reported. Humidity
errors are percentage points; temperature errors are °C; moisture errors are
index units.

Generated evidence comprises six window NPZs, validation JSON (including source
and code hashes), origin manifest, cumulative/lead-time metric CSVs, text
summary, four actual-versus-persistence plots and one lead-error plot. Each
example uses the first eligible origin rather than selecting a favourable
prediction. The complete future timeline, issue time, units and synthetic
disclaimer appear on plots. The JSON and each tabular/NPZ output also contain
the synthetic disclaimer. Standard-library tests cover malformed inputs,
quality rules, node isolation, causal filling, window timing, split leakage,
metric arithmetic and independently recomputed saved-artifact scores.

Attention-based BiLSTM remains the primary planned model; standard LSTM and
GRU remain the planned learned baselines. None is implemented or trained in
Phase 1. See `docs/c2/PP1_Microclimate_Phase1_Traceability.md` for traceability.
