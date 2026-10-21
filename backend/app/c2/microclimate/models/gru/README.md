# C2 standard GRU baseline

**Synthetic Data — Prototype Evaluation Only**

The fixed architecture is `Input(336,3) → GRU(32) → RepeatVector(168) →
GRU(32,return_sequences=True) → TimeDistributed(Dense(3))`: **9,987 parameters**.
GRU uses Keras defaults (`reset_after=True`, tanh/sigmoid). This is a learned
baseline; the proposal's primary Attention BiLSTM is not implemented here.

The existing frozen scaled NPZ files supply 11,137 training windows, 1,622
validation windows and 811 test windows per node. Feature order, masks, split
boundaries, 160/168 eligible-hour rule and training-fitted scalers are unchanged.
Moisture is an INDEX, temperature is °C and humidity error is in percentage points.

`model.py` inherits the existing masked optimization/build/call/config methods
and creates only GRU layers. `common/masked_loss.py` supplies eligible-element
selection and SSE/count normalization. `train.py` reuses existing dataset loaders,
tf.data batching, epoch callback and artifact hashing. `evaluation.py` reuses
the original metric functions and reads frozen LSTM predictions; `inference.py`
reuses the original inference contract after registering the GRU custom model.
The LSTM implementation and artifacts are not modified or retrained.

Adam .001, global clipping 1, batch 16, maximum 100 epochs, patience 10,
validation masked MSE, restored best weights and seed 42 are fixed before training.
CPU float32 uses six intra-op threads, one inter-op thread, deterministic operations,
training-only shuffle buffer 1,024 and full final partial batches. Seed 42 is reset
after disposable unit tests before research model creation.

Targets with mask=False contribute zero loss/gradient and no evaluated error.
Only historical X enters the network. Predictions are inverse-transformed using
the frozen target scaler. Persistence uses the input inverse and last historical
values. Labels, masks, origins and Persistence values must match the saved LSTM
artifacts exactly before the three-model comparison is generated.

From `backend/`, using the existing environment:

```powershell
# Training requires a NEW experiment directory.
.\.venv\Scripts\python.exe -B -u -m app.c2.microclimate.models.gru.train --output experiments/c2/microclimate/gru_v1_reproduction

# Fresh-process reload and complete saved-test prediction replay; no training.
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.gru.verification --experiment experiments/c2/microclimate/gru_v1

# Output must be a NEW file inside the chosen checkpoint's experiment directory.
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.gru.inference --model experiments/c2/microclimate/gru_v1/gru_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/gru_v1/inference_new_NODE_01.npz

.\.venv\Scripts\python.exe -B -m unittest discover -s app/c2/microclimate -t . -v
```

The verifier writes GRU verification logs/report updates inside the supplied GRU
experiment; it never trains or writes LSTM outputs. Training will not overwrite an
existing directory. Check the executed report and `training_report.json` for the
actual completion status, epochs, runtime and scores; source code alone is not
evidence of a completed training run.

Expected evidence under `backend/experiments/c2/microclimate/gru_v1/` includes
`gru_best.keras`, first-epoch and best-validation checkpoints, frozen scaler copy,
config/history/runtime, architecture, per-node prediction NPZs, original-unit
masked metrics, three-model comparison, plots, hashes, tests and
`PP1_GRU_Implementation_Report.md`.

The cumulative metrics cover leads 1–24, 1–72 and 1–168 hours. Pooled metrics
concatenate eligible forecast/observation pairs. Overlapping origins are dependent;
one seed and fixed synthetic generator do not establish real-world superiority.
No real Sri Lankan Nai Miris field accuracy, C1 validation, external climate-data
integration or growth-stage labels are claimed. Existing LSTM test results have
already been inspected, so this is comparative prototype evidence rather than a
new untouched real-field test.
