# Step 3 — train-only input and target standardization

**Synthetic Data — Prototype Evaluation Only**

This stage reads the existing `phase1_masked` tensors and original synthetic
CSV. It never regenerates windows, changes masks/splits, trains a model or
overwrites either unscaled experiment. All outputs are versioned under
`backend/experiments/c2/microclimate/phase1_masked_scaled/`.

## Reproduce

Run from the repository root in PowerShell using the existing backend venv:

```powershell
Push-Location backend
try {
    .\.venv\Scripts\python.exe -B -m app.c2.microclimate.preprocessing.run_phase1_scaled
    .\.venv\Scripts\python.exe -B -m unittest app.c2.microclimate.preprocessing.tests.test_phase1 app.c2.microclimate.preprocessing.tests.test_phase1_masked app.c2.microclimate.preprocessing.tests.test_scaling -v
} finally {
    Pop-Location
}
```

The earlier complete-case and masked artifacts must exist. Do not rerun their
generators to reproduce this step: they are protected inputs. No new packages
are needed. The pipeline uses NumPy/pandas; its StandardScaler-equivalence
test uses the already installed scikit-learn. Integration tests require this
stage's generated artifacts and fail if they are missing.

## Exact fitting policy

Two distinct scalers are fitted, both shared across the two nodes:

* **Input:** unique original `(node_id,timestamp)` observations appearing in
  retained training histories, filtered by original source quality.
* **Target:** unique original `(node_id,timestamp)` observations appearing in
  retained training target windows, filtered by original source quality.

Each source key contributes once per role, regardless of how many overlapping
windows contain it. Two nodes at the same timestamp remain distinct spatial
observations. Samples are pooled by observation, not weighted by window
frequency or averaged into equally weighted node means. Shared scaling gives
one consistent input/target feature space and preserves between-node offsets
in the common-unit synthetic data. It does not assert real sensor calibration.

The fitting rows exclude INVALID, anomalous and supplied-imputed observations.
Historical values reconstructed by forward fill are **not** fitting samples.
Clean WARN would remain eligible under the unchanged quality policy. Source
rows are cut to the frozen training interval before any numeric statistics.
Only training archive origin identifiers are consulted before fitting; neither
validation nor test values/coverage selects the scalers. Target fitting never
uses labels after the training boundary. All offsets stay inside their
original node/partition.

Actual unique fit counts per feature: input **11,724** (5,865 NODE_01 and
5,859 NODE_02); target **11,391** (5,698 NODE_01 and 5,693 NODE_02).
The input pool runs Jan 1 00:00–Sep 6 11:00; target pool Jan 15 00:00–
Sep 13 11:00, 2025, Asia/Colombo. These differences arise from the 336/168
window roles; means/stds are therefore legitimately different.

For each feature, `z = (value - mean) / scale`, using population variance
(`ddof=0`) as in StandardScaler. Parameters are computed/stored in float64;
transformed model arrays are float32. A zero/numerically constant feature
uses scale=1 while retaining its measured std (possibly zero) in metadata.
No eligible fitting observations is an error, not a default fabricated mean.
There is no clipping, target interpolation or change to the 160/168 rule.

## Tensor and mask contract

Feature/target order is strictly checked:
`soil_moisture_avg_index`, `air_temperature_c`, `relative_humidity_pct`.

Each scaled NPZ contains finite float32 `X: [N,336,3]` and `y: [N,168,3]`.
Every inherited metadata array, origin, `target_valid_mask: [N,168,3]` and
`history_valid_mask: [N,336]` is preserved. The source NPZs remain unchanged.

Historical X values, including causal forward fills, are transformed with the
input scaler; history masks still identify genuine versus filled positions.
Target transformation selects mask=True positions **before arithmetic**.
Masked-out y values are replaced with **0 in standardized space** solely as a
finite storage placeholder. Zero is never treated as a target label. The
mask must be used in every loss and evaluation; it is never a model input.
NaN/Inf/extreme excluded values cannot affect fitting, transformed targets or
the existing masked reference loss. Framework-specific differentiable loss
integration remains a later neural-network task.

For inverse transforms, input histories use the input scaler and model
predictions use the target scaler. They are not interchangeable. Predictions
return to moisture **INDEX** units (not VWC), temperature °C and humidity % RH.
Actual-target inverse transformation returns NaN at mask=False positions so
that the zero placeholder cannot masquerade as the training mean observation.

```python
import json
import numpy as np
from app.c2.microclimate.preprocessing.scaling import Standardizer
from app.c2.microclimate.preprocessing.pipeline import TARGETS

saved = json.loads((output / "scalers.json").read_text(encoding="utf-8"))
target_scaler = Standardizer.from_dict(saved["target"])
# predictions_scaled must have last dimension 3 in TARGETS order:
predictions_original_units = target_scaler.inverse_transform(predictions_scaled, TARGETS)
actual_original_units = target_scaler.inverse_targets(y, target_valid_mask, TARGETS)
```

NPZs load with `np.load(path, allow_pickle=False)`. The scaled-parameter SHA-256
is stored in each archive. JSON persistence requires no pickle execution.
Repeated/filled window arrays need not have exact empirical mean zero/std one:
the unique genuine fitting pool defines those statistics, not window weighting.

## Execution evidence and limits

The pipeline saves scaler JSON, the two auditable fitting-row CSVs, six NPZs,
an unchanged origin manifest, validation/preservation reports, summary and
original-unit persistence reproduction tables. It does not generate new
forecast models or graphs. The CSV and all 38 artifacts from the two earlier
experiments are hashed before/after execution (39 protected files total).

Float32 quantization means inverse recovery is approximate. A predeclared
absolute tolerance of `1e-5` in each original unit is enforced for inverse
arrays and baseline metrics, with no relative tolerance. All 54 cumulative
and 3,024 lead-time metric rows and denominators are compared with the prior
masked experiment. Reported numerical errors and 54-test results are in
`docs/c2/PP1_Microclimate_Scaling.md` and versioned evidence files.

No scaling blocker remains for these existing tensors. Model-specific batching
and differentiable masked-loss use still require Phase 2 verification. Quality
provenance, stale fills, overlapping forecasts and synthetic-only generalization
limits remain. NASA POWER, ERA5-Land, growth-stage integration, LSTM, GRU and
Attention BiLSTM are not added in this step. Yield and C1/C3/C4 are untouched.
