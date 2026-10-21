# Standard LSTM baseline — full-cohort experiment

**Synthetic Data — Prototype Evaluation Only**

This is the planned standard LSTM learned baseline, not the primary Attention
BiLSTM. It consumes the existing `phase1_masked_scaled` archives unchanged.
No GRU, attention model, source-data/scaler change or external climate data is
introduced. No real Sri Lankan Nai Miris field performance is established.

## Exact architecture and optimization

`Input(336,3) -> LSTM(32) -> RepeatVector(168) ->
LSTM(32,return_sequences=True) -> TimeDistributed(Dense(3))`.
13,027 parameters. Default LSTM tanh/sigmoid activations, no dropout,
bidirectionality or state carried between windows. Targets remain moisture
INDEX, air temperature °C and relative humidity % in their fixed order.

Adam learning rate .001, global gradient clip norm 1, batch size 16, maximum
100 epochs. EarlyStopping monitors `val_loss`, patience 10,
`restore_best_weights=True`. ModelCheckpoint saves the minimum validation-loss
model. All 11,137 eligible training windows and 1,622 validation windows are
used, including the final partial batch. A seeded 1,024-window training-only
shuffle buffer is used; validation is not shuffled. Seed 42 is set before
preflight/model creation; TensorFlow operation determinism is requested.
Six intra-op threads, one inter-op thread, a two-thread data input pool,
prefetch one, and 16 steps per compiled execution limit overhead/memory.
CPU float32, no mixed precision or XLA compilation.

## Explicit supervision masks

The network receives historical X only. The custom train/test steps unpack
the third dataset element as the boolean `[N,168,3]` target mask. Eligible
actuals/predictions are selected with `tf.boolean_mask` before subtraction.
Loss is sum of squared errors / valid-element count in standardized target
space. Excluded target positions contribute exactly zero gradient; placeholder
zeros never become observations. Zero-valid batches skip optimizer updates.
Epoch training/validation losses aggregate SSE and valid-element counts, not
unweighted batch losses. The existing 160/168 quality policy is unchanged.

The original historical masks stay in the input archives. This baseline does
not add mask channels or apply `Masking(mask_value=0)` to standardized X, since
zero is also a legitimate standardized value. It uses the existing causal
filled three-channel history exactly as prepared.

## Run from the repository root (PowerShell)

```powershell
Push-Location backend
try {
    .\.venv\Scripts\python.exe -B -u -m app.c2.microclimate.models.lstm.train
} finally {
    Pop-Location
}
```

The trainer executes all 54 preprocessing and 10 new LSTM/loss tests BEFORE
training, including gradient, epoch-denominator and model save/reload tests.
It refuses to overwrite an existing experiment directory. For reproduction:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe -B -u -m app.c2.microclimate.models.lstm.train --output experiments/c2/microclimate/lstm_v1_reproduction
Pop-Location
```

Use a new output directory for each run. CPU timing and floating-point results
can vary across hardware/library settings; environment versions and exact
configuration are recorded. No model file is claimed to reproduce real fields.

## Checkpoints, evaluation and inference

`first_epoch.keras` is saved after the first successful epoch;
`best_validation.keras` is the best validation checkpoint;
`lstm_best.keras` is the selected reloadable inference model. History/runtime
evidence is written after each completed epoch, including measured seconds.
Trained-model test predictions and scores are computed only after validation
selection. Preflight preprocessing tests may inspect test arrays solely for
integrity checks; those values do not fit weights or select a model. Test
predictions are inverse-transformed with the frozen **target** scaler.
Persistence is constructed using the **input** scaler inverse and the last
historical value, evaluated on exactly the same target mask positions.

Original-unit masked MAE/RMSE/R² are reported per node/target and cumulatively
over leads 1–24, 1–72, 1–168. Pooled results concatenate the two nodes' eligible
observations; they do not average MAE/RMSE/R². R² is unavailable for fewer than
two eligible observations or zero target variation. Target counts repeat
timestamps across overlapping forecasts and are not independent sample counts.

```powershell
Push-Location backend
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.lstm.verification --experiment experiments/c2/microclimate/lstm_v1 --evidence-dir "$env:TEMP/c2-lstm-verification"
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.lstm.inference --model experiments/c2/microclimate/lstm_v1/lstm_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/lstm_v1/inference_refactor_NODE_01.npz
Pop-Location
```

Inference loads with `compile=False`, uses historical inputs only and never
fits or trains. Its output path must be new. All model classes are registered
through `lstm_model.py`; preserve that module when loading `.keras` models.

The experiment saves architecture, configuration/seed, first/best checkpoints,
history, runtime, loss curves, two timestamped forecast plots, per-node/pooled
metrics, lead metrics, persistence comparisons, prediction NPZs and preservation
hashes. Finite actual arrays in evaluation NPZs retain inverse-transformed
placeholders at mask=False; they are not ground truth. Plot gaps and all
metrics respect the masks. See the executed experiment report for actual
epochs, runtime and results; a model is not declared trained just because this
README or its code exists.
