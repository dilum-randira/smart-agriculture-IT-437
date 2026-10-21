# Primary Attention BiLSTM microclimate forecaster

**Synthetic Data — Prototype Evaluation Only**

Architecture: `Input(336,3) → Bidirectional(LSTM(32, return_sequences=True)) →
TemporalAttention(32) → Dense(32,relu) → Dense(504) → Reshape(168,3)`.
There are **30,040 parameters**: encoder 9,216, attention 2,112, context Dense 2,080,
forecast Dense 16,632. Both LSTM directions operate only on available history.

For each 64-dimensional historical encoder state, attention computes
`e_t = vᵀ tanh(W h_t + b)`, `alpha = softmax(e, time)`, and
`context = Σ_t alpha_t h_t`. The projection width is 32; the score Dense has
no redundant scalar bias. Keras stores the projection kernel as W transposed.
Weights are finite nonnegative `[N,336]` arrays summing to one. A single global
historical context supports all 168×3 outputs. Weights are **descriptive, not causal**
and are not separate explanations for each target/horizon.

Frozen data/scalers, 336/168 windows, three-feature order, 160-valid-hour eligibility,
node isolation and calendar splits remain unchanged. All 11,137 training windows
and 1,622 validation windows are used; each node has 811 held-out test windows.
Masked target entries have zero loss/gradient. Predictions use the TARGET scaler
inverse; Persistence uses the INPUT scaler inverse. Soil moisture is INDEX, not VWC;
temperature is °C and humidity errors are percentage points.

Training is fixed before evaluation: Adam .001, global clipping 1, batch 16,
maximum 100 epochs, patience 10, masked validation MSE, restored best weights,
seed 42 reset after fixture tests, CPU float32 with six/one TensorFlow threads,
deterministic operations, training-only shuffle buffer 1,024 and full final batches.
No hyperparameter selection uses held-out metrics. Status and actual completed
epochs/runtime/scores must be read from the generated evidence, not inferred from code.

Only X enters the network. The encoder's backward direction reverses within the
historical input window, never the future target window. Causally filled historical
values participate in the same model input policy as LSTM/GRU. Historical quality
masks are retained for inspection and visualized; they do not introduce new features
or silently change attention normalization. No future weather, crop-stage labels,
real C1 measurements, planting dates or external climate data are introduced.

The model inherits the proven masked model methods, constructing only its own
forecaster. `common/experiment.py` reuses existing data loaders, batching, masked
loss, epoch callback and hash protection. `common/comparison.py` performs generic
multi-model evaluation using existing metric functions and frozen reference
predictions. `common/plotting.py` supplies multi-model plots. Existing LSTM, GRU
and preprocessing implementations are untouched.

Run from `backend/` in the existing environment:

```powershell
# Requires a NEW output directory; the completed attention_bilstm_v1 is preserved.
.\.venv\Scripts\python.exe -B -u -m app.c2.microclimate.models.attention_bilstm.train --output experiments/c2/microclimate/attention_bilstm_v1_reproduction

# Fresh-process prediction/attention replay, without training; logs stay in this experiment.
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.attention_bilstm.verification --experiment experiments/c2/microclimate/attention_bilstm_v1

# Requires a NEW output filename inside the chosen checkpoint directory.
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.attention_bilstm.inference --model experiments/c2/microclimate/attention_bilstm_v1/attention_bilstm_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/attention_bilstm_v1/inference_new_NODE_01.npz

.\.venv\Scripts\python.exe -B -m unittest discover -s app/c2/microclimate -t . -v
```

Existing LSTM verification supports `--evidence-dir` for external logs. Existing GRU
verification writes reports to its supplied experiment; preservation verification
must run it on an external COPY, not on frozen `gru_v1`. Neither baseline is retrained.

New outputs live under `backend/experiments/c2/microclimate/attention_bilstm_v1/`:
three checkpoints, frozen scaler copy, history/config/runtime/architecture, source
and input provenance, per-node forecasts, 108 cumulative metric rows, 6,048 lead
rows, 27 four-model comparison rows with per-metric descriptive winners, curves,
forecast plots, attention CSV/NPZ/PNG and the executed PP1 report.

The attention examples are the fixed first chronological test window of each node,
chosen independently of error or attention concentration. Historical plots show
all 336 timestamps ending at the forecast origin. Gray points mark past-filled
inputs. These weights describe the fitted network's historical-state weighting;
encoder states themselves mix history, so attention does not establish causal
importance, irrigation effects or real agronomic explainability.

Limitations include synthetic provenance, unknown future irrigation/weather,
stale historical fills, dependent overlapping windows, one seed/configuration and
repeated use of the same inspected test for planned model comparisons. No external
validation, statistically significant superiority or real-field accuracy is claimed.
See the completed experiment's `training_report.json`, `test_metrics.csv`,
`four_model_comparison.csv` and `PP1_Attention_BiLSTM_Report.md` for actual evidence.
