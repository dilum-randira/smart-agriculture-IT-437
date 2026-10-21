# PP1 GRU baseline — executed evidence

**Synthetic Data — Prototype Evaluation Only**

This fixed standard GRU is a learned baseline. Attention BiLSTM remains unimplemented.
Synthetic results do not establish accuracy on real Sri Lankan Nai Miris field measurements.

## Architecture and completed training

Input(336,3) → GRU(32) → RepeatVector(168) → GRU(32,return_sequences=True)
→ TimeDistributed(Dense(3)). **9,987 parameters**; Keras default reset_after=True,
tanh/sigmoid, no dropout, no bidirectionality. Soil moisture is INDEX, not VWC.

All 11,137 training and 1,622 validation windows were used. Frozen partition,
feature, mask, 160/168 eligibility and training-only scaler contracts are unchanged.
Adam .001, global clip norm 1, batch 16, maximum 100 epochs, patience 10,
restore best weights, seed 42. CPU float32, 6/1 TensorFlow threads, deterministic
operations, 1,024 training-only shuffle buffer and complete final partial batch.
The seed is reset after fixture tests before research model initialization.

Completed **32 epochs**; best validation epoch **22**.
Actual fit duration **2116.717 seconds**
(35.279 minutes).
Training masked MSE at selected epoch **0.073904321**;
best validation masked MSE **0.073405881**.
Minimum training loss over all epochs **0.069830501**.
Selection uses validation only; held-out predictions follow checkpoint selection.
No hyperparameters were changed in response to test scores.

## Supervision and comparable held-out evaluation

Reuses the existing masked train/test steps, element selection before arithmetic,
SSE/valid-element loss normalization, valid-weighted epoch metric, empty-supervision
update guard, frozen NPZ loaders, tf.data batching, epoch callback and metric functions.
Only historical X enters the network; target masks are supervision. Masked target
placeholders never constitute genuine ground truth or enter evaluated errors.

Each node has 811 unchanged test origins. LSTM predictions are read from preserved
artifacts. Actual eligible labels, timestamps, masks and Persistence arrays are
asserted identical before comparison. Predictions use the target scaler inverse;
Persistence uses the input scaler inverse. Cumulative leads are 1–24, 1–72, 1–168.
Pooled metrics concatenate eligible pairs; they do not average node RMSE or R².
R² is unitless and unavailable for insufficient/constant actual values. Errors are
moisture INDEX units, air temperature °C and relative humidity percentage points.

| Model | Node | Target | Hours | Valid pairs | MAE | RMSE | R² |
|---|---|---|---|---|---|---|---|
| Persistence | NODE_01 | soil_moisture_avg_index | 24 | 19190 | 1.39158 | 1.80311 | 0.83479 |
| Persistence | NODE_01 | soil_moisture_avg_index | 72 | 57590 | 1.97373 | 2.53466 | 0.63633 |
| Persistence | NODE_01 | soil_moisture_avg_index | 168 | 134495 | 2.70147 | 3.39420 | 0.16102 |
| Persistence | NODE_01 | air_temperature_c | 24 | 19190 | 2.92497 | 3.59619 | -0.99111 |
| Persistence | NODE_01 | air_temperature_c | 72 | 57590 | 2.92762 | 3.59614 | -0.99444 |
| Persistence | NODE_01 | air_temperature_c | 168 | 134495 | 2.92990 | 3.59693 | -0.99247 |
| Persistence | NODE_01 | relative_humidity_pct | 24 | 19190 | 10.23303 | 12.59017 | -0.99797 |
| Persistence | NODE_01 | relative_humidity_pct | 72 | 57590 | 10.23262 | 12.57144 | -1.00975 |
| Persistence | NODE_01 | relative_humidity_pct | 168 | 134495 | 10.22126 | 12.54962 | -1.01606 |
| LSTM | NODE_01 | soil_moisture_avg_index | 24 | 19190 | 2.64079 | 3.55636 | 0.35730 |
| LSTM | NODE_01 | soil_moisture_avg_index | 72 | 57590 | 2.36024 | 3.04280 | 0.47590 |
| LSTM | NODE_01 | soil_moisture_avg_index | 168 | 134495 | 2.22567 | 2.84403 | 0.41096 |
| LSTM | NODE_01 | air_temperature_c | 24 | 19190 | 0.65214 | 0.78521 | 0.90507 |
| LSTM | NODE_01 | air_temperature_c | 72 | 57590 | 0.65020 | 0.77583 | 0.90717 |
| LSTM | NODE_01 | air_temperature_c | 168 | 134495 | 0.67058 | 0.79856 | 0.90179 |
| LSTM | NODE_01 | relative_humidity_pct | 24 | 19190 | 3.11213 | 3.63019 | 0.83389 |
| LSTM | NODE_01 | relative_humidity_pct | 72 | 57590 | 3.09895 | 3.60044 | 0.83515 |
| LSTM | NODE_01 | relative_humidity_pct | 168 | 134495 | 3.13691 | 3.64373 | 0.83004 |
| GRU | NODE_01 | soil_moisture_avg_index | 24 | 19190 | 2.45273 | 3.06287 | 0.52329 |
| GRU | NODE_01 | soil_moisture_avg_index | 72 | 57590 | 2.38711 | 2.98576 | 0.49536 |
| GRU | NODE_01 | soil_moisture_avg_index | 168 | 134495 | 2.21935 | 2.80485 | 0.42708 |
| GRU | NODE_01 | air_temperature_c | 24 | 19190 | 0.57363 | 0.70663 | 0.92312 |
| GRU | NODE_01 | air_temperature_c | 72 | 57590 | 0.57274 | 0.70242 | 0.92391 |
| GRU | NODE_01 | air_temperature_c | 168 | 134495 | 0.58548 | 0.71678 | 0.92088 |
| GRU | NODE_01 | relative_humidity_pct | 24 | 19190 | 2.75056 | 3.24186 | 0.86753 |
| GRU | NODE_01 | relative_humidity_pct | 72 | 57590 | 2.75071 | 3.24278 | 0.86628 |
| GRU | NODE_01 | relative_humidity_pct | 168 | 134495 | 2.76863 | 3.25842 | 0.86409 |
| Persistence | NODE_02 | soil_moisture_avg_index | 24 | 19076 | 1.47132 | 1.90522 | 0.74454 |
| Persistence | NODE_02 | soil_moisture_avg_index | 72 | 57164 | 2.08010 | 2.67449 | 0.39932 |
| Persistence | NODE_02 | soil_moisture_avg_index | 168 | 133368 | 2.76721 | 3.57932 | -0.51920 |
| Persistence | NODE_02 | air_temperature_c | 24 | 19076 | 2.90255 | 3.56759 | -0.99224 |
| Persistence | NODE_02 | air_temperature_c | 72 | 57164 | 2.90108 | 3.56363 | -0.99730 |
| Persistence | NODE_02 | air_temperature_c | 168 | 133368 | 2.90284 | 3.56377 | -0.99492 |
| Persistence | NODE_02 | relative_humidity_pct | 24 | 19076 | 10.12765 | 12.44065 | -0.99593 |
| Persistence | NODE_02 | relative_humidity_pct | 72 | 57164 | 10.12390 | 12.42326 | -1.00762 |
| Persistence | NODE_02 | relative_humidity_pct | 168 | 133368 | 10.10742 | 12.39733 | -1.01511 |
| LSTM | NODE_02 | soil_moisture_avg_index | 24 | 19076 | 2.73647 | 3.69188 | 0.04075 |
| LSTM | NODE_02 | soil_moisture_avg_index | 72 | 57164 | 2.56983 | 3.21785 | 0.13045 |
| LSTM | NODE_02 | soil_moisture_avg_index | 168 | 133368 | 2.69744 | 3.28033 | -0.27599 |
| LSTM | NODE_02 | air_temperature_c | 24 | 19076 | 0.53071 | 0.72011 | 0.91883 |
| LSTM | NODE_02 | air_temperature_c | 72 | 57164 | 0.50670 | 0.68438 | 0.92634 |
| LSTM | NODE_02 | air_temperature_c | 168 | 133368 | 0.50278 | 0.66865 | 0.92977 |
| LSTM | NODE_02 | relative_humidity_pct | 24 | 19076 | 2.27958 | 2.95709 | 0.88723 |
| LSTM | NODE_02 | relative_humidity_pct | 72 | 57164 | 2.20899 | 2.87202 | 0.89270 |
| LSTM | NODE_02 | relative_humidity_pct | 168 | 133368 | 2.19427 | 2.84775 | 0.89367 |
| GRU | NODE_02 | soil_moisture_avg_index | 24 | 19076 | 2.74331 | 3.18758 | 0.28491 |
| GRU | NODE_02 | soil_moisture_avg_index | 72 | 57164 | 2.68786 | 3.13854 | 0.17278 |
| GRU | NODE_02 | soil_moisture_avg_index | 168 | 133368 | 2.76050 | 3.23834 | -0.24354 |
| GRU | NODE_02 | air_temperature_c | 24 | 19076 | 0.48933 | 0.65747 | 0.93234 |
| GRU | NODE_02 | air_temperature_c | 72 | 57164 | 0.48486 | 0.64782 | 0.93400 |
| GRU | NODE_02 | air_temperature_c | 168 | 133368 | 0.49465 | 0.64844 | 0.93395 |
| GRU | NODE_02 | relative_humidity_pct | 24 | 19076 | 2.17147 | 2.85364 | 0.89498 |
| GRU | NODE_02 | relative_humidity_pct | 72 | 57164 | 2.14999 | 2.82544 | 0.89616 |
| GRU | NODE_02 | relative_humidity_pct | 168 | 133368 | 2.13983 | 2.80250 | 0.89702 |
| Persistence | POOLED | soil_moisture_avg_index | 24 | 38266 | 1.43133 | 1.85472 | 0.81065 |
| Persistence | POOLED | soil_moisture_avg_index | 72 | 114754 | 2.02672 | 2.60525 | 0.57433 |
| Persistence | POOLED | soil_moisture_avg_index | 168 | 267863 | 2.73420 | 3.48760 | -0.00716 |
| Persistence | POOLED | air_temperature_c | 24 | 38266 | 2.91379 | 3.58196 | -0.97238 |
| Persistence | POOLED | air_temperature_c | 72 | 114754 | 2.91440 | 3.57999 | -0.97631 |
| Persistence | POOLED | air_temperature_c | 168 | 267863 | 2.91643 | 3.58046 | -0.97403 |
| Persistence | POOLED | relative_humidity_pct | 24 | 38266 | 10.18050 | 12.51585 | -0.96346 |
| Persistence | POOLED | relative_humidity_pct | 72 | 114754 | 10.17846 | 12.49784 | -0.97437 |
| Persistence | POOLED | relative_humidity_pct | 168 | 267863 | 10.16458 | 12.47402 | -0.98052 |
| LSTM | POOLED | soil_moisture_avg_index | 24 | 38266 | 2.68849 | 3.62455 | 0.27687 |
| LSTM | POOLED | soil_moisture_avg_index | 72 | 114754 | 2.46465 | 3.13123 | 0.38510 |
| LSTM | POOLED | soil_moisture_avg_index | 168 | 267863 | 2.46056 | 3.06902 | 0.22009 |
| LSTM | POOLED | air_temperature_c | 24 | 38266 | 0.59161 | 0.75346 | 0.91273 |
| LSTM | POOLED | air_temperature_c | 72 | 114754 | 0.57872 | 0.73170 | 0.91744 |
| LSTM | POOLED | air_temperature_c | 168 | 267863 | 0.58703 | 0.73675 | 0.91642 |
| LSTM | POOLED | relative_humidity_pct | 24 | 38266 | 2.69710 | 3.31178 | 0.86252 |
| LSTM | POOLED | relative_humidity_pct | 72 | 114754 | 2.65562 | 3.25800 | 0.86583 |
| LSTM | POOLED | relative_humidity_pct | 168 | 267863 | 2.66758 | 3.27171 | 0.86376 |
| GRU | POOLED | soil_moisture_avg_index | 24 | 38266 | 2.59759 | 3.12566 | 0.46223 |
| GRU | POOLED | soil_moisture_avg_index | 72 | 114754 | 2.53693 | 3.06282 | 0.41168 |
| GRU | POOLED | soil_moisture_avg_index | 168 | 267863 | 2.48879 | 3.02845 | 0.24057 |
| GRU | POOLED | air_temperature_c | 24 | 38266 | 0.53161 | 0.68257 | 0.92838 |
| GRU | POOLED | air_temperature_c | 72 | 114754 | 0.52896 | 0.67577 | 0.92958 |
| GRU | POOLED | air_temperature_c | 168 | 267863 | 0.54026 | 0.68361 | 0.92804 |
| GRU | POOLED | relative_humidity_pct | 24 | 38266 | 2.46188 | 3.05450 | 0.88305 |
| GRU | POOLED | relative_humidity_pct | 72 | 114754 | 2.45147 | 3.04205 | 0.88303 |
| GRU | POOLED | relative_humidity_pct | 168 | 267863 | 2.45555 | 3.03998 | 0.88237 |

GRU RMSE is lower than Persistence in **21/27**
node/pooled-target-horizon rows and lower than LSTM in
**27/27** rows. These descriptive counts do
not establish statistical significance or real-field superiority.

## Valid eligible forecast/observation pairs

| node | target | window_hours | valid_observations | masked_observations |
|---|---|---|---|---|
| NODE_01 | soil_moisture_avg_index | 24 | 19190 | 274 |
| NODE_01 | soil_moisture_avg_index | 72 | 57590 | 802 |
| NODE_01 | soil_moisture_avg_index | 168 | 134495 | 1753 |
| NODE_01 | air_temperature_c | 24 | 19190 | 274 |
| NODE_01 | air_temperature_c | 72 | 57590 | 802 |
| NODE_01 | air_temperature_c | 168 | 134495 | 1753 |
| NODE_01 | relative_humidity_pct | 24 | 19190 | 274 |
| NODE_01 | relative_humidity_pct | 72 | 57590 | 802 |
| NODE_01 | relative_humidity_pct | 168 | 134495 | 1753 |
| NODE_02 | soil_moisture_avg_index | 24 | 19076 | 388 |
| NODE_02 | soil_moisture_avg_index | 72 | 57164 | 1228 |
| NODE_02 | soil_moisture_avg_index | 168 | 133368 | 2880 |
| NODE_02 | air_temperature_c | 24 | 19076 | 388 |
| NODE_02 | air_temperature_c | 72 | 57164 | 1228 |
| NODE_02 | air_temperature_c | 168 | 133368 | 2880 |
| NODE_02 | relative_humidity_pct | 24 | 19076 | 388 |
| NODE_02 | relative_humidity_pct | 72 | 57164 | 1228 |
| NODE_02 | relative_humidity_pct | 168 | 133368 | 2880 |
| POOLED | soil_moisture_avg_index | 24 | 38266 | 662 |
| POOLED | soil_moisture_avg_index | 72 | 114754 | 2030 |
| POOLED | soil_moisture_avg_index | 168 | 267863 | 4633 |
| POOLED | air_temperature_c | 24 | 38266 | 662 |
| POOLED | air_temperature_c | 72 | 114754 | 2030 |
| POOLED | air_temperature_c | 168 | 267863 | 4633 |
| POOLED | relative_humidity_pct | 24 | 38266 | 662 |
| POOLED | relative_humidity_pct | 72 | 114754 | 2030 |
| POOLED | relative_humidity_pct | 168 | 267863 | 4633 |

## Verification and reproducibility

Preflight: 77 tests passed, no failures/errors/skips.
Post-training verification: {'evaluation_label': 'Synthetic Data — Prototype Evaluation Only', 'tests_run': 6, 'failures': 0, 'errors': 0, 'skipped': 0}.
The best checkpoint is `gru_best.keras`; `first_epoch.keras` and
`best_validation.keras` retain epoch and validation-selection evidence. Frozen
scalers are copied byte-for-byte. Existing data, experiments and LSTM artifacts
match their pre-run hashes. Fresh-process verification independently recalculates
metrics and replays both full saved test prediction arrays.

From backend, using the existing venv (training output must be new):

```powershell
.\.venv\Scripts\python.exe -B -u -m app.c2.microclimate.models.gru.train --output experiments/c2/microclimate/gru_v1_reproduction
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.gru.verification --experiment experiments/c2/microclimate/gru_v1
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.gru.inference --model experiments/c2/microclimate/gru_v1/gru_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/gru_v1/inference_new_NODE_01.npz
.\.venv\Scripts\python.exe -B -m unittest discover -s app/c2/microclimate -t . -v
```

Evidence includes training config/history/runtime, architecture, source/input
hashes, three checkpoints, frozen scalers, per-node predictions, 81 cumulative
metric rows, per-lead metrics, 27 three-model comparison rows, loss curves and
timestamped forecast plots. Existing outputs are never reused as training output.

## Limitations

- 100% synthetic; no real Sri Lankan Nai Miris field validation.
- Overlapping origins are dependent forecast/observation pairs.
- Single fixed seed/configuration; no significance or generalization claim.
- Existing test results have already been inspected for LSTM; this is comparative prototype evidence.
- Missing future irrigation/weather and stale historical fills limit forecasts.
- Pooled R² includes between-node variation and is not interchangeable with node R².
- No NASA POWER/ERA5-Land integration, fabricated growth stages or real C1 input.
- The fixed GRU is unidirectional and is not the proposal's primary attention model.


## Final verification and changed files

Executed on October 21, 2026, branch `feature/c2-predictive-intelligence`, using Python 3.11.9 / TensorFlow 2.21.0 / Keras 3.15.1 in `backend/.venv`.

**88 distinct automated tests passed; 0 failures, errors or skips:** 77 existing/new unit tests, six GRU saved-artifact tests, five preserved LSTM artifact tests. The 77-test suite passed both before and after full training. Disposable fixture optimizer updates do not retrain the research LSTM.

Fresh-process replay matched all 811 test windows per node exactly: maximum scaled and original-unit differences both **0.0**. The fresh-process inference CLI also executed on all NODE_01 test windows, produced finite `[811,168,3]` predictions and matched saved predictions/timestamps.

Training used all 11,137 windows (697 batches/epoch, including the final one-window batch). Validation used all 1,622 windows (102 batches/epoch), with 805,122 valid scalar target elements every epoch. The six saved-artifact tests verified optimizer updates at the selected epoch, original-unit metrics, pooled counts, identical masks/timestamps and protected-file hashes.

Created under `backend/app/c2/microclimate/models/gru/`:

- `model.py`
- `train.py`
- `inference.py`
- `evaluation.py`
- `reporting.py`
- `verification.py`
- `tests/__init__.py`
- `tests/test_gru.py`
- `README.md`

Also created this PP1 document and all GRU artifacts under `backend/experiments/c2/microclimate/gru_v1/`. The only modified pre-existing file is `backend/app/c2/microclimate/README.md`, to document GRU availability. No existing Python implementation, dataset, scaler, split, LSTM checkpoint, plot, metric or research result changed. SHA-256 checks verified the other **217 pre-existing files** are byte-identical. No packages were installed, no commits/pushes made and no deployment performed.

Shared code was reused without editing LSTM: masked model methods, eligible-element loss/count accumulator, scaled data contract/loaders, dataset batching, epoch-evidence callback, hashing, metric functions, inference and Markdown-table rendering. No Attention BiLSTM or external climate integration was added.

Evidence links: [full metrics](../../backend/experiments/c2/microclimate/gru_v1/test_metrics.csv), [three-model comparison](../../backend/experiments/c2/microclimate/gru_v1/three_model_comparison.csv), [training history](../../backend/experiments/c2/microclimate/gru_v1/training_history.csv), [verification summary](../../backend/experiments/c2/microclimate/gru_v1/verification_summary.json), [GRU guide](../../backend/app/c2/microclimate/models/gru/README.md).

## Interpretation for PP1

GRU has lower measured RMSE than the frozen LSTM in all 27 comparison rows. Persistence still has lower soil-moisture RMSE at 24h and 72h for both nodes and the pooled cohort. NODE_02 soil-moisture R? at 168h is **-0.243536**; the model underperforms the eligible-actual mean reference used by R? for that cohort. Pooled R? does not replace node-specific analysis. These are descriptive synthetic comparisons, not evidence of field accuracy or statistically established superiority.

## Execution notes and remaining blockers

No implementation or compatibility blocker remains. TensorFlow native-Windows CPU and existing Keras/NumPy deprecation warnings were observed. The initial PowerShell redirection wrapper returned status 1 while recording TensorFlow stderr as NativeCommandError; the Python training log contains `GRU_FULL_TRAINING_COMPLETE` and no traceback. All 32 epochs, selection, evaluation and report generation completed. Fresh subprocess verification and inference subsequently exited **0**; no second research training run was needed. The original console record is retained in `training_console.txt`.

Audit hash inventory and raw verification logs: `C:\Users\Asus\AppData\Local\C2GRUAudit\20261021-165623`.
