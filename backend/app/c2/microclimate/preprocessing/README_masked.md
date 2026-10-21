# C2 Phase 1 — target validity masks

**Synthetic Data — Prototype Evaluation Only**

This version fixes complete-case target rejection while preserving the original
336-hour history, 168-hour forecast and three targets in their original units.
There is no scaling, model implementation, training, tuning or external climate
integration. The original `phase1/` experiment is never overwritten.

## Reproduce from the repository root (PowerShell)

```powershell
Push-Location backend
try {
    .\.venv\Scripts\python.exe -B -m app.c2.microclimate.preprocessing.run_phase1_masked
    .\.venv\Scripts\python.exe -B -m unittest app.c2.microclimate.preprocessing.tests.test_phase1 app.c2.microclimate.preprocessing.tests.test_phase1_masked -v
} finally {
    Pop-Location
}
```

Run the pipeline before the tests: the new integration tests require its saved
artifacts. The new entry point always writes to
`backend/experiments/c2/microclimate/phase1_masked/`. It checks the source hash
and exact split boundaries against the original Phase 1 report and verifies a
SHA-256 inventory of the CSV and every original Phase 1 artifact before/after
execution. Reruns overwrite only this version's generated evidence and refuse
to proceed if protected files differ from its first-run preservation manifest.

## Exact eligibility and mask policy

Before any forward filling, original row quality defines validity:

```python
valid = ~(record_status.eq("INVALID") | is_anomaly | is_imputed)
```

For a future observation, this boolean is repeated across the three target
channels. `target_valid_mask` has shape `[N,168,3]`; True/1 is an eligible
synthetic observation, False/0 must never contribute to loss or metrics.
WARN is eligible only when neither anomalous nor supplied-imputed. This is a
conservative whole-row policy even if only a moisture sensor was imputed.

Require finite historical inputs and **at least 95% valid hours per target**:
`ceil(.95 * 168) = 160`. Thus no empty-label window can be retained. The
training-only quality analysis found median coverage of 165/168 hours at both
nodes, minima of 161/168 and 157/168, and 121 NODE_02 training windows below
160. The 95% operational floor retains the majority of training observations
while screening the lower-coverage tail. It is not an empirically optimal
threshold and was not selected from validation/test errors. The fixed rule is
applied unchanged to validation and test. See `development_quality.json`.

`X` is still created by causal, node-local, partition-local historical
forward fill. Its observation mask remains `[N,336]`. **`y` is the unchanged
raw source values**, including untrusted values at mask=False; it is never
interpolated or filled. Always load/use `target_valid_mask` together with y.
Targets and target masks are supervision metadata, not future model inputs.

## Frozen chronology and tensor contract

Default boundaries remain exactly those in the original report (Asia/Colombo):
training Jan 1 00:00–Sep 13 11:00, validation Sep 13 12:00–Nov 7 05:00,
test Nov 7 06:00–Dec 31 23:00, all in 2025. All 336 historical and 168
future timestamps stay within one node and partition. No cross-split history
borrowing, backward filling or fitted preprocessing occurs.

Each versioned NPZ contains `X: [N,336,3]`, `y: [N,168,3]`,
`target_valid_mask: [N,168,3]` (bool), `history_valid_mask: [N,336]`,
origin timestamps as UTC Unix nanoseconds, target/feature names, timezone,
eligibility fraction and synthetic disclaimer. Target order remains:

1. `soil_moisture_avg_index`: index, **not volumetric water content**.
2. `air_temperature_c`: °C.
3. `relative_humidity_pct`: % RH (error in percentage points).

Use `np.load(path, allow_pickle=False)`. For origin t, input times are
t−335..t hours and targets are t+1..t+168 hours. The sample manifest records
these endpoints and each window's usable hours.

## Masked evaluation and loss contract

`masked_scores()` selects eligible positions **before subtraction**, so even
NaN/Inf or extreme values at excluded positions cannot contaminate a result.
For each node/target/cumulative horizon (1–24, 1–72, 1–168) and lead:

```
MAE  = sum(abs(prediction - actual) at mask=True) / count(mask=True)
RMSE = sqrt(sum((prediction - actual)^2 at mask=True) / count(mask=True))
```

Zero denominators return unavailable metrics (`None`, blank in CSV), not zero
error. Tables report eligible forecast samples, contributing samples, valid,
masked and possible observation counts and coverage. Forecast-origin counts
are distinct from unique valid target timestamps; the JSON reports both.
Rolling windows overlap, so scored counts are not independent observations.

`masked_regression_loss()` provides a tested NumPy MSE/MAE reference with the
same denominator/exclusion contract. It does not train anything or provide a
differentiable neural-network loss. Phase 2 must enforce these same masks in
its framework-specific loss; an ordinary unmasked loss on saved y is invalid.
No joint cross-unit model objective or scaling is chosen in this step.

Plots show gaps for masked targets; persistence remains a full 168-hour
forecast from the last valid historical value. Neither the forecast nor X
receives future masks or observations. The old `windows()`/`scores()` interfaces
remain complete-case and continue passing all original 20 tests.

## Evidence and limitations

Generated outputs include six NPZs, six actual/persistence plots, a lead-error
plot, cumulative and lead metric CSVs, sample manifest, training-quality JSON,
validation JSON, preservation manifest and summary. Test results are recorded
in the versioned `test_results.txt`. Full coverage and results are in
`docs/c2/PP1_Microclimate_Target_Masking.md`.

Counts increase because partially observed forecasts are retained, not because
labels were invented. These scores cannot be directly interpreted as improved
performance over the old complete-case scores: the evaluated sample set is
different. Missingness may be informative, quality flags lack full provenance,
and historical fills can be stale. All data remains synthetic; no local field
accuracy, sensor calibration or real C1 validation is established. Scaling,
LSTM/GRU/Attention BiLSTM, NASA POWER, ERA5-Land and growth-stage integration
remain outside this step.
