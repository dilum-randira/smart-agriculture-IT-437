# C2 standard LSTM baseline — PP1 implementation evidence

**Synthetic Data — Prototype Evaluation Only**

The standard LSTM baseline was actually trained on all 11,137 eligible training
windows in the existing Windows CPU backend environment. It is not the planned
primary Attention BiLSTM. No new data, scaling fit, quality policy, split,
GRU, attention model, external dataset or deployment was introduced.

Architecture: **Input(336,3) → LSTM(32) → RepeatVector(168) →
LSTM(32, return_sequences=True) → TimeDistributed(Dense(3))**.
**13,027 trainable neural-network parameters.** Adam .001, global clip norm 1,
batch 16, seed 42, maximum 100 epochs, validation early stopping patience 10,
best-weight restoration and best-validation checkpointing. Each epoch used
697 batches, including its final partial batch. Validation used 1,622 windows.

**Completed: 21 epochs. Best: epoch 11. Total fit: 1,085.933 seconds
(18.099 minutes). Mean epoch: 51.692 seconds.** Best-epoch training/validation
masked standardized MSE: **0.07535882 / 0.08226760**. Final-epoch training/
validation losses: **0.07046118 / 0.08998938**. The requested early-stopping
protocol completed; the run was not manually interrupted.

Only X enters the network. Target masks select eligible elements before error
arithmetic, and loss normalizes by valid count. False positions have zero
gradient. Epoch loss aggregates SSE/count, not average batch losses. Zero-valid
batches skip updates. All existing arrays/masks remain finite and unchanged.

The minimum-validation checkpoint was frozen before trained-model test
predictions. Preflight preprocessing tests may inspect test data for integrity;
those checks do not fit weights or select models. All test results use the
original 811 windows per node and the original eligible target positions.

Pooled 168-hour masked results (MAE / RMSE):

| Target | LSTM | Persistence | LSTM R² |
|---|---:|---:|---:|
| Moisture INDEX | 2.4606 / 3.0690 | 2.7342 / 3.4876 | 0.2201 |
| Temperature °C | 0.5870 / 0.7367 | 2.9164 / 3.5805 | 0.9164 |
| Humidity percentage points | 2.6676 / 3.2717 | 10.1646 / 12.4740 | 0.8638 |

Each pooled target/horizon has 38,266 / 114,754 / 267,863 valid forecast/target
pairs at 24 / 72 / 168 hours. Counts overlap in time and are not independent
observations. Pooling concatenates observations, not node metric averages.

The LSTM has lower RMSE in 21/27 node/pooled × target × horizon comparisons.
It is better on temperature/humidity at all reported horizons, worse on soil
moisture at 24/72 hours, and better on soil moisture at 168 hours. NODE_02
168-hour moisture R² remains **−0.2760**: lower error than persistence does not
establish strong explanatory performance. Synthetic daily cycles are prominent;
these results demonstrate no real Sri Lankan Nai Miris field accuracy.

**Verification: 64/64 preflight tests** (54 existing + 10 new model/loss tests),
plus **5/5 post-training integration tests**. No failures/errors/skips.
Reload consistency discrepancy: 0. Standalone fresh-process inference on all
811 NODE_01 test windows reproduced the saved predictions exactly, without
retraining. All 77 protected upstream artifacts match their pre-run hashes.

Evidence lives in
[`backend/experiments/c2/microclimate/lstm_v1/`](../../backend/experiments/c2/microclimate/lstm_v1/):

- [`lstm_best.keras`](../../backend/experiments/c2/microclimate/lstm_v1/lstm_best.keras), first-epoch and best-validation checkpoints.
- [Full held-out report](../../backend/experiments/c2/microclimate/lstm_v1/PP1_LSTM_Implementation_Report.md), including all node/target/horizon MAE/RMSE tables.
- [MAE/RMSE/R² and counts](../../backend/experiments/c2/microclimate/lstm_v1/test_metrics.csv), lead metrics and persistence comparisons.
- [Loss curve](../../backend/experiments/c2/microclimate/lstm_v1/loss_curves.png), both forecast plots, training history/runtime/configuration and architecture.
- Frozen scaler copy, prediction arrays, preflight/post-training logs, input provenance, preservation and standalone-inference verification.

New implementation is under `backend/app/c2/microclimate/`: `lstm_model.py`,
`lstm_evaluation.py`, `train_lstm.py`, `test_lstm.py`, `infer_lstm.py`,
`verify_lstm_artifacts.py`, `lstm_reporting.py` and `README_lstm.md`.
Previous Yield and C1/C3/C4 implementations were not modified.

From `backend/`, using the existing venv:

```powershell
.\.venv\Scripts\python.exe -B -u -m app.c2.microclimate.models.lstm.train --output experiments/c2/microclimate/lstm_v1_reproduction
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.lstm.verification --experiment experiments/c2/microclimate/lstm_v1 --evidence-dir "$env:TEMP/c2-lstm-verification"
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.lstm.inference --model experiments/c2/microclimate/lstm_v1/lstm_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/lstm_v1/inference_reproduction_NODE_01.npz
```

Use new output names when rerunning; existing experiments are not overwritten.
Next: review this evidence and implement the planned GRU using the same data
contract and development-only selection. Do not tune against the inspected
test results or interpret synthetic scores as validated field performance.
