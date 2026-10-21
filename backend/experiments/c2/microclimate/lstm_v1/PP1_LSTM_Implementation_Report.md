# PP1 standard LSTM baseline — executed implementation report

**Synthetic Data — Prototype Evaluation Only**

Model is the standard LSTM baseline, not the primary Attention BiLSTM.
The existing synthetic 336-hour history to 168-hour/three-target mapping,
training-only scalers, 160/168 target eligibility, masks and chronological
splits were preserved. No real Sri Lankan Nai Miris field accuracy is established.

## Actual training

Architecture: Input(336,3) → LSTM(32) → RepeatVector(168) →
LSTM(32,return_sequences=True) → TimeDistributed(Dense(3)). **13,027 parameters.**
All **11,137** eligible training windows and **1,622** validation windows used.
Adam lr .001, global clip norm 1, batch 16, seed 42, maximum 100 epochs,
EarlyStopping patience 10, restore best weights; best checkpoint chosen solely
by validation masked MSE. CPU threads 6 intra-op / 1 inter-op. Training-only
shuffle buffer 1,024; full final partial batches retained. No tuning or model
change based on held-out results.

Completed **21 epochs**, best epoch **11**.
Total fit duration **1085.93 seconds**
(18.10 minutes); mean epoch
51.69 seconds including validation (checkpoint
overhead is included in total fit time). Best-epoch training masked MSE:
**0.07535882**; best validation masked MSE:
**0.08226760**. Final-epoch training/validation losses:
0.07046118 / 0.08998938.
Stopped early: **True**.

## Correct supervision and evaluation

Only historical X enters the network. TensorFlow selects mask=True actuals and
predictions before subtraction. Loss normalizes by the valid-element count;
false elements contribute zero gradient. Epoch loss aggregates error sums and
counts, never unweighted batch losses. Empty-label batches skip optimization.
The same mask logic is used for training and validation. Targets remain finite
placeholder arrays paired with explicit masks.

After validation-only checkpoint selection, the frozen model was reloaded and
evaluated on 811 test windows per node. Predictions use the TARGET scaler
inverse. Persistence uses the INPUT scaler inverse and last historical values.
Both models are scored on exactly the same eligible test elements. All
reported errors below are in original units: moisture INDEX (not VWC), °C,
and humidity percentage points. R² is in `test_metrics.csv`; it is unitless,
can be negative, and is unavailable if actual variation/count is insufficient.

## Complete held-out masked MAE / RMSE

| Model | Node | Target | 1–24h | 1–72h | 1–168h |
|---|---|---|---|---|---|
| LSTM | NODE_01 | soil_moisture_avg_index | 2.6408 / 3.5564 | 2.3602 / 3.0428 | 2.2257 / 2.8440 |
| LSTM | NODE_01 | air_temperature_c | 0.6521 / 0.7852 | 0.6502 / 0.7758 | 0.6706 / 0.7986 |
| LSTM | NODE_01 | relative_humidity_pct | 3.1121 / 3.6302 | 3.0989 / 3.6004 | 3.1369 / 3.6437 |
| Persistence | NODE_01 | soil_moisture_avg_index | 1.3916 / 1.8031 | 1.9737 / 2.5347 | 2.7015 / 3.3942 |
| Persistence | NODE_01 | air_temperature_c | 2.9250 / 3.5962 | 2.9276 / 3.5961 | 2.9299 / 3.5969 |
| Persistence | NODE_01 | relative_humidity_pct | 10.2330 / 12.5902 | 10.2326 / 12.5714 | 10.2213 / 12.5496 |
| LSTM | NODE_02 | soil_moisture_avg_index | 2.7365 / 3.6919 | 2.5698 / 3.2179 | 2.6974 / 3.2803 |
| LSTM | NODE_02 | air_temperature_c | 0.5307 / 0.7201 | 0.5067 / 0.6844 | 0.5028 / 0.6687 |
| LSTM | NODE_02 | relative_humidity_pct | 2.2796 / 2.9571 | 2.2090 / 2.8720 | 2.1943 / 2.8478 |
| Persistence | NODE_02 | soil_moisture_avg_index | 1.4713 / 1.9052 | 2.0801 / 2.6745 | 2.7672 / 3.5793 |
| Persistence | NODE_02 | air_temperature_c | 2.9025 / 3.5676 | 2.9011 / 3.5636 | 2.9028 / 3.5638 |
| Persistence | NODE_02 | relative_humidity_pct | 10.1276 / 12.4407 | 10.1239 / 12.4233 | 10.1074 / 12.3973 |
| LSTM | POOLED | soil_moisture_avg_index | 2.6885 / 3.6245 | 2.4646 / 3.1312 | 2.4606 / 3.0690 |
| LSTM | POOLED | air_temperature_c | 0.5916 / 0.7535 | 0.5787 / 0.7317 | 0.5870 / 0.7367 |
| LSTM | POOLED | relative_humidity_pct | 2.6971 / 3.3118 | 2.6556 / 3.2580 | 2.6676 / 3.2717 |
| Persistence | POOLED | soil_moisture_avg_index | 1.4313 / 1.8547 | 2.0267 / 2.6053 | 2.7342 / 3.4876 |
| Persistence | POOLED | air_temperature_c | 2.9138 / 3.5820 | 2.9144 / 3.5800 | 2.9164 / 3.5805 |
| Persistence | POOLED | relative_humidity_pct | 10.1805 / 12.5159 | 10.1785 / 12.4978 | 10.1646 / 12.4740 |

## Valid observation counts

| Node | Target | 1–24h | 1–72h | 1–168h |
|---|---|---|---|---|
| NODE_01 | soil_moisture_avg_index | 19190 | 57590 | 134495 |
| NODE_01 | air_temperature_c | 19190 | 57590 | 134495 |
| NODE_01 | relative_humidity_pct | 19190 | 57590 | 134495 |
| NODE_02 | soil_moisture_avg_index | 19076 | 57164 | 133368 |
| NODE_02 | air_temperature_c | 19076 | 57164 | 133368 |
| NODE_02 | relative_humidity_pct | 19076 | 57164 | 133368 |
| POOLED | soil_moisture_avg_index | 38266 | 114754 | 267863 |
| POOLED | air_temperature_c | 38266 | 114754 | 267863 |
| POOLED | relative_humidity_pct | 38266 | 114754 | 267863 |

Pooled metrics concatenate eligible observations rather than averaging node
metrics. Pooled R² includes between-node variation and can differ substantially
from individual-node R². Repeated target/forecast pairs across overlapping
origins are not independent observations.

LSTM has lower RMSE in **21/27** node/pooled × target ×
horizon rows. This descriptive comparison is not a significance test or proof
of real-field superiority. Detailed MAE/RMSE percentage differences are in
`persistence_comparison.csv`.

## Verification and saved evidence

Preflight: 64 passed, zero failures/errors/skips. Post-training integration: 5 run, 0 failures, 0 errors.
Saved-model reload maximum prediction discrepancy during selection verification:
0.0. Trained model: **`lstm_best.keras`**.
`first_epoch.keras` and `best_validation.keras` are also retained. Upstream
data/scalers/models/experiment artifacts match their pre-run hashes.

Evidence: `training_history.csv`, `runtime.json`, `training_config.json`,
`architecture.txt`, `loss_curves.png`, `forecast_NODE_01.png`,
`forecast_NODE_02.png`, `test_metrics.csv`, `test_lead_metrics.csv`,
`persistence_comparison.csv`, per-node prediction NPZs, checkpoint files,
preflight/post-training logs and provenance/preservation JSON. Plot examples
use the first chronological test origin, not an error-selected example.
Masked actual positions appear as gaps. Finite actual placeholders in NPZs
remain mask-excluded, never measured ground truth.

## Reproduction and frozen inference

Run commands from `backend/` with its existing venv. A training output directory
must be new; an existing directory is never overwritten.

```powershell
.\.venv\Scripts\python.exe -B -u -m app.c2.microclimate.train_lstm --output experiments/c2/microclimate/lstm_v1_reproduction
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.verify_lstm_artifacts --experiment experiments/c2/microclimate/lstm_v1
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.infer_lstm --model experiments/c2/microclimate/lstm_v1/lstm_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/lstm_v1/inference_reproduction_NODE_01.npz
```

Inference loads the model with compile=False and performs no retraining. Import
the project's registered custom model module when loading the .keras artifact.
Use a new inference output filename if rerunning.

## Limits and next step

This is one fixed standard-LSTM baseline on synthetic data. Synthetic generation
and imputation provenance, stale forward fills, dependent rolling windows and
unobserved future irrigation/weather limit conclusions. No GRU, Attention
BiLSTM, external climate fusion, growth-stage labels or deployment is added.
After reviewing this evidence, implement the planned GRU on the same fixed
windows/masks/scalers and validation protocol; reserve test data from tuning.
The current test has now been inspected and is no longer untouched evidence
for subsequent human design decisions.
