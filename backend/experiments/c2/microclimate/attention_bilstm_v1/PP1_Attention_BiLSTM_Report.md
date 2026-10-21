# PP1 Attention BiLSTM — completed primary-model evidence

**Synthetic Data — Prototype Evaluation Only**

This is the proposal's primary historical Attention BiLSTM. Results do not establish
real Sri Lankan Nai Miris field accuracy or statistically significant superiority.

## Exact architecture and attention

Input(336,3) → Bidirectional LSTM(32 per direction, return_sequences=True)
→ TemporalAttention(projection width 32) → context(64) → Dense(32,relu)
→ Dense(504,linear) → Reshape(168,3). **30,040 parameters**:
encoder 9,216; attention 2,112; context dense 2,080; forecast dense 16,632.

For historical encoder state h_t in R^64:
`e_t = v^T tanh(W h_t + b)`, with W in R^(32×64), b in R^32, v in R^32.
`alpha_t = exp(e_t) / sum_s exp(e_s)` over the 336 historical steps;
`context = sum_t alpha_t h_t`. The score has no redundant scalar bias.
Attention weights are finite nonnegative `[N,336]`, sum to one, and receive
nonzero training gradients. One global temporal summary feeds all outputs; these
are not per-target or per-horizon causal explanations.

Both encoder directions see ONLY the historical window, including its existing
causally forward-filled inputs. Reversing within available history is not access
to future target observations. Historical quality flags are retained for inspection
but are not additional model features or a newly introduced history-attention mask.
All 336 states participate in the normalization, matching the specified architecture.

## Full fixed training protocol

All 11,137 training and 1,622 validation windows were used. Original scalers,
336/168/3 windows, 160-valid-hour eligibility, node isolation and chronological
partitions remain frozen. Masked labels never enter the loss or gradient.
The existing shared loss selects eligible elements before subtraction and divides
SSE by their count. Epoch MSE is valid-element weighted; empty-label batches skip
optimizer updates. Only historical X enters model.call.

Adam .001, global gradient clip 1, batch 16, max 100 epochs, early-stopping
patience 10, validation masked MSE, restore best weights, seed 42 (reset after
unit fixtures), CPU float32, six/one intra/inter-op threads, deterministic operations,
training-only shuffle buffer 1,024 and complete final partial batches.

Completed **15 epochs**; selected **epoch 5**.
Fit duration **932.120 seconds**
(15.535 minutes).
Selected-epoch training masked MSE **0.076213202**;
best validation masked MSE **0.076356699**;
minimum training masked MSE **0.070056475**.
Selection and weight restoration were completed before trained-model held-out
inference. Test scores did not alter this single fixed configuration.

## Complete primary-model held-out metrics

811 unchanged test origins per node. Errors use the frozen TARGET scaler inverse:
moisture INDEX (not VWC), temperature °C, humidity percentage points. Persistence
uses the INPUT scaler inverse. Actual labels, masks, origins and Persistence
values match both frozen learned baselines. Pooled metrics concatenate eligible
observation/forecast pairs rather than averaging node scores. R² is unitless and
unavailable for insufficient or constant actuals. Masked finite placeholders are
never trusted labels. Counts refer to dependent rolling-window forecast pairs.

| Node | Target | Cumulative hours | Valid pairs | MAE | RMSE | R² |
|---|---|---|---|---|---|---|
| NODE_01 | soil_moisture_avg_index | 24 | 19190 | 2.055328 | 2.548186 | 0.670042 |
| NODE_01 | soil_moisture_avg_index | 72 | 57590 | 2.156864 | 2.689413 | 0.590565 |
| NODE_01 | soil_moisture_avg_index | 168 | 134495 | 2.144532 | 2.693996 | 0.471470 |
| NODE_01 | air_temperature_c | 24 | 19190 | 0.618505 | 0.748874 | 0.913657 |
| NODE_01 | air_temperature_c | 72 | 57590 | 0.629980 | 0.757659 | 0.911469 |
| NODE_01 | air_temperature_c | 168 | 134495 | 0.654975 | 0.780892 | 0.906090 |
| NODE_01 | relative_humidity_pct | 24 | 19190 | 3.072227 | 3.563462 | 0.839944 |
| NODE_01 | relative_humidity_pct | 72 | 57590 | 3.080531 | 3.576040 | 0.837379 |
| NODE_01 | relative_humidity_pct | 168 | 134495 | 3.043234 | 3.533347 | 0.840186 |
| NODE_02 | soil_moisture_avg_index | 24 | 19076 | 2.085992 | 2.560323 | 0.538652 |
| NODE_02 | soil_moisture_avg_index | 72 | 57164 | 2.111990 | 2.595768 | 0.434158 |
| NODE_02 | soil_moisture_avg_index | 168 | 133368 | 2.191639 | 2.692476 | 0.140359 |
| NODE_02 | air_temperature_c | 24 | 19076 | 0.489414 | 0.660597 | 0.931693 |
| NODE_02 | air_temperature_c | 72 | 57164 | 0.493008 | 0.659971 | 0.931497 |
| NODE_02 | air_temperature_c | 168 | 133368 | 0.491285 | 0.647076 | 0.934232 |
| NODE_02 | relative_humidity_pct | 24 | 19076 | 2.188945 | 2.832619 | 0.896525 |
| NODE_02 | relative_humidity_pct | 72 | 57164 | 2.177049 | 2.829596 | 0.895850 |
| NODE_02 | relative_humidity_pct | 168 | 133368 | 2.134081 | 2.790810 | 0.897882 |
| POOLED | soil_moisture_avg_index | 24 | 38266 | 2.070614 | 2.554243 | 0.640884 |
| POOLED | soil_moisture_avg_index | 72 | 114754 | 2.134511 | 2.643179 | 0.561847 |
| POOLED | soil_moisture_avg_index | 168 | 267863 | 2.167986 | 2.693239 | 0.399385 |
| POOLED | air_temperature_c | 24 | 38266 | 0.554152 | 0.706248 | 0.923323 |
| POOLED | air_temperature_c | 72 | 114754 | 0.561749 | 0.710677 | 0.922118 |
| POOLED | air_temperature_c | 168 | 267863 | 0.573474 | 0.717392 | 0.920752 |
| POOLED | relative_humidity_pct | 24 | 38266 | 2.631902 | 3.219931 | 0.870044 |
| POOLED | relative_humidity_pct | 72 | 114754 | 2.630467 | 3.225867 | 0.868462 |
| POOLED | relative_humidity_pct | 168 | 267863 | 2.590570 | 3.185351 | 0.870854 |

## Four-model RMSE comparison and descriptive winners

| Node | Target | Hours | Persistence | LSTM | GRU | AttentionBiLSTM | Lowest RMSE |
|---|---|---|---|---|---|---|---|
| NODE_01 | soil_moisture_avg_index | 24 | 1.803109 | 3.556358 | 3.062872 | 2.548186 | Persistence |
| NODE_01 | soil_moisture_avg_index | 72 | 2.534656 | 3.042805 | 2.985756 | 2.689413 | Persistence |
| NODE_01 | soil_moisture_avg_index | 168 | 3.394201 | 2.844025 | 2.804846 | 2.693996 | AttentionBiLSTM |
| NODE_01 | air_temperature_c | 24 | 3.596192 | 0.785212 | 0.706635 | 0.748874 | GRU |
| NODE_01 | air_temperature_c | 72 | 3.596145 | 0.775831 | 0.702417 | 0.757659 | GRU |
| NODE_01 | air_temperature_c | 168 | 3.596934 | 0.798556 | 0.716779 | 0.780892 | GRU |
| NODE_01 | relative_humidity_pct | 24 | 12.590166 | 3.630188 | 3.241856 | 3.563462 | GRU |
| NODE_01 | relative_humidity_pct | 72 | 12.571439 | 3.600441 | 3.242785 | 3.576040 | GRU |
| NODE_01 | relative_humidity_pct | 168 | 12.549616 | 3.643730 | 3.258421 | 3.533347 | GRU |
| NODE_02 | soil_moisture_avg_index | 24 | 1.905222 | 3.691875 | 3.187579 | 2.560323 | Persistence |
| NODE_02 | soil_moisture_avg_index | 72 | 2.674489 | 3.217854 | 3.138539 | 2.595768 | AttentionBiLSTM |
| NODE_02 | soil_moisture_avg_index | 168 | 3.579322 | 3.280327 | 3.238339 | 2.692476 | AttentionBiLSTM |
| NODE_02 | air_temperature_c | 24 | 3.567586 | 0.720111 | 0.657473 | 0.660597 | GRU |
| NODE_02 | air_temperature_c | 72 | 3.563633 | 0.684375 | 0.647819 | 0.659971 | GRU |
| NODE_02 | air_temperature_c | 168 | 3.563766 | 0.668652 | 0.648439 | 0.647076 | AttentionBiLSTM |
| NODE_02 | relative_humidity_pct | 24 | 12.440650 | 2.957087 | 2.853644 | 2.832619 | AttentionBiLSTM |
| NODE_02 | relative_humidity_pct | 72 | 12.423261 | 2.872019 | 2.825438 | 2.829596 | GRU |
| NODE_02 | relative_humidity_pct | 168 | 12.397328 | 2.847753 | 2.802501 | 2.790810 | AttentionBiLSTM |
| POOLED | soil_moisture_avg_index | 24 | 1.854717 | 3.624548 | 3.125662 | 2.554243 | Persistence |
| POOLED | soil_moisture_avg_index | 72 | 2.605251 | 3.131228 | 3.062817 | 2.643179 | Persistence |
| POOLED | soil_moisture_avg_index | 168 | 3.487601 | 3.069021 | 3.028446 | 2.693239 | AttentionBiLSTM |
| POOLED | air_temperature_c | 24 | 3.581960 | 0.753462 | 0.682570 | 0.706248 | GRU |
| POOLED | air_temperature_c | 72 | 3.579986 | 0.731703 | 0.675771 | 0.710677 | GRU |
| POOLED | air_temperature_c | 168 | 3.580458 | 0.736746 | 0.683607 | 0.717392 | GRU |
| POOLED | relative_humidity_pct | 24 | 12.515854 | 3.311785 | 3.054502 | 3.219931 | GRU |
| POOLED | relative_humidity_pct | 72 | 12.497844 | 3.258004 | 3.042052 | 3.225867 | GRU |
| POOLED | relative_humidity_pct | 168 | 12.474025 | 3.271713 | 3.039979 | 3.185351 | GRU |

`test_metrics.csv` includes all 108 model/node/target/horizon rows with MAE/RMSE/R²;
`four_model_comparison.csv` includes 27 rows with valid counts and winners for
MAE, RMSE and R². Ties within absolute 1e-12 are retained as joint winners.
No aggregate error across targets with incompatible units is reported.

## Attention evidence and verification

Representative windows are fixed first chronological test origins for each node,
not selected by forecast error or attention concentration. CSV/NPZ/PNG attention
artifacts record 336 historical timestamps, weights, historical model inputs,
original-quality mask and origin. Gray points denote causally filled inputs.
Weights summarize encoded historical states, which themselves mix the full
history bidirectionally; a high weight is not a causal effect or proof of agronomic
importance. No growth-stage labels, crop ages, external climate or real IoT inputs
were fabricated. Soil irrigation transitions may remain unpredictable from X alone.

Preflight tests: {'tests_run': 89, 'failures': 0, 'errors': 0, 'skipped': 0}. Post-training artifact tests: {'evaluation_label': 'Synthetic Data — Prototype Evaluation Only', 'tests_run': 8, 'failures': 0, 'errors': 0, 'skipped': 0}.
Aggregate regression verification: {'evaluation_label': 'Synthetic Data — Prototype Evaluation Only', 'automated_tests': {'unit_tests': 89, 'attention_artifact_tests': 8, 'lstm_artifact_tests': 5, 'gru_artifact_tests_on_external_copy': 6, 'total': 108, 'failures': 0, 'errors': 0, 'skipped': 0}, 'inference_cli': 'passed', 'preexisting_files_checked': 262, 'unchanged': True, 'original_gru_artifacts_untouched': True}.
Selected/restored model discrepancy before held-out evaluation:
0.0. Fresh-process verification separately replays
the stored test predictions and attention weights without retraining. Existing
datasets, scaler files, LSTM/GRU source/checkpoints/results remain protected by hashes.

## Reproduction (from backend)

```powershell
.\.venv\Scripts\python.exe -B -u -m app.c2.microclimate.models.attention_bilstm.train --output experiments/c2/microclimate/attention_bilstm_v1_reproduction
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.attention_bilstm.verification --experiment experiments/c2/microclimate/attention_bilstm_v1
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.attention_bilstm.inference --model experiments/c2/microclimate/attention_bilstm_v1/attention_bilstm_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/attention_bilstm_v1/inference_new_NODE_01.npz
.\.venv\Scripts\python.exe -B -m unittest discover -s app/c2/microclimate -t . -v
```

Training output must be new. Inference output must be a new filename inside the
chosen checkpoint directory. Verification writes logs only to this new experiment.
Artifacts include first_epoch.keras, best_validation.keras, attention_bilstm_best.keras,
frozen scaler copy, provenance, source hashes, config, architecture, history/runtime,
per-node predictions, cumulative/per-lead metrics, comparisons, forecast and
attention figures, tests and reload evidence. No baseline retraining is performed.

## Limitations and remaining PP1 tasks

- 100% synthetic; no real Sri Lankan Nai Miris field validation.
- Attention is descriptive, not causal or independent proof of explainability.
- Overlapping origins are dependent forecast/observation pairs.
- Single fixed configuration/seed; repeated use of the same test is not external validation.
- Historical forward fills and unknown future irrigation/weather limit interpretation.
- Attention weights are descriptive and not causally faithful explanations.
- A pooled R² can conceal weak node-specific skill; inspect each node and target.
- Present per-target baseline comparisons honestly, including any losses to Persistence.
- Prepare the viva demonstration and slides using these frozen artifacts; avoid tuning
  against the inspected test set. Real C1 provenance/measurement calibration and future
  independently collected field validation remain later research tasks, not PP1 evidence.
