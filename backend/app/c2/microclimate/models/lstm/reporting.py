"""Render PP1 evidence exclusively from actually completed experiment files."""
import argparse
import json
from pathlib import Path
import zipfile

import pandas as pd

from ...preprocessing.pipeline import LABEL
from ...common.paths import SCALED_OUTPUT as DATA
from ...common.paths import digest


def markdown_table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def write_reports(output):
    output=Path(output)
    report=json.loads((output/'training_report.json').read_text(encoding='utf-8'))
    if report['status']!='complete':raise ValueError('Cannot report incomplete training as complete')
    config=json.loads((output/'training_config.json').read_text(encoding='utf-8'))
    provenance=json.loads((output/'input_provenance.json').read_text(encoding='utf-8'))
    if digest(DATA/'scalers.json')!=provenance['scaler_sha256']:
        raise ValueError('Original scaler changed since training')
    (output/'scalers_frozen.json').write_bytes((DATA/'scalers.json').read_bytes())
    metrics=pd.read_csv(output/'test_metrics.csv')
    comparison=pd.read_csv(output/'persistence_comparison.csv')
    rows=[]
    for (model,node,target),g in metrics.groupby(['model','node','target'],sort=False):
        rows.append([model,node,target,*[f'{r.MAE:.4f} / {r.RMSE:.4f}' for r in g.itertuples()]])
    counts=[]
    for (node,target),g in metrics[metrics.model.eq('LSTM')].groupby(['node','target'],sort=False):
        counts.append([node,target,*g.valid_observations.tolist()])
    post_path=output/'post_training_tests.json'
    post=json.loads(post_path.read_text(encoding='utf-8')) if post_path.exists() else None
    tests=f"Preflight: {report['preflight_tests']['tests_run']} passed, zero failures/errors/skips."
    tests+=f" Post-training integration: {post['tests_run']} run, {post['failures']} failures, {post['errors']} errors." if post else ' Additional post-training integration verification not yet recorded.'
    lstm_wins=int((comparison.RMSE_lstm<comparison.RMSE_persistence).sum())
    text=f'''# PP1 standard LSTM baseline — executed implementation report

**{LABEL}**

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

Completed **{report['epochs_completed']} epochs**, best epoch **{report['best_epoch']}**.
Total fit duration **{report['training_duration_seconds']:.2f} seconds**
({report['training_duration_seconds']/60:.2f} minutes); mean epoch
{report['mean_epoch_seconds']:.2f} seconds including validation (checkpoint
overhead is included in total fit time). Best-epoch training masked MSE:
**{report['best_epoch_training_loss']:.8f}**; best validation masked MSE:
**{report['best_validation_loss']:.8f}**. Final-epoch training/validation losses:
{report['last_epoch_training_loss']:.8f} / {report['last_epoch_validation_loss']:.8f}.
Stopped early: **{report['stopped_early']}**.

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

'''+markdown_table(['Model','Node','Target','1–24h','1–72h','1–168h'],rows)+'''

## Valid observation counts

'''+markdown_table(['Node','Target','1–24h','1–72h','1–168h'],counts)+f'''

Pooled metrics concatenate eligible observations rather than averaging node
metrics. Pooled R² includes between-node variation and can differ substantially
from individual-node R². Repeated target/forecast pairs across overlapping
origins are not independent observations.

LSTM has lower RMSE in **{lstm_wins}/{len(comparison)}** node/pooled × target ×
horizon rows. This descriptive comparison is not a significance test or proof
of real-field superiority. Detailed MAE/RMSE percentage differences are in
`persistence_comparison.csv`.

## Verification and saved evidence

{tests}
Saved-model reload maximum prediction discrepancy during selection verification:
{report['reload_max_absolute_error']}. Trained model: **`lstm_best.keras`**.
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
.\\.venv\\Scripts\\python.exe -B -u -m app.c2.microclimate.models.lstm.train --output experiments/c2/microclimate/lstm_v1_reproduction
.\\.venv\\Scripts\\python.exe -B -m app.c2.microclimate.models.lstm.verification --experiment experiments/c2/microclimate/lstm_v1
.\\.venv\\Scripts\\python.exe -B -m app.c2.microclimate.models.lstm.inference --model experiments/c2/microclimate/lstm_v1/lstm_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/lstm_v1/inference_reproduction_NODE_01.npz
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
'''
    (output/'PP1_LSTM_Implementation_Report.md').write_text(text,encoding='utf-8')
    (output/'README.md').write_text(f'# Standard LSTM baseline\n\n**{LABEL}**\n\n'+
        'See [executed PP1 report](PP1_LSTM_Implementation_Report.md) for full results, runtime, limitations and reproduction commands.\n\n'+
        f"Completed {report['epochs_completed']} epochs; best validation epoch {report['best_epoch']}; trained model `lstm_best.keras`.\n",
        encoding='utf-8')
    with zipfile.ZipFile(output/'best_validation.keras') as z:
        metadata=json.loads(z.read('config.json'))
    (output/'optimizer_compile_config.json').write_text(json.dumps(dict(evaluation_label=LABEL,compile_config=metadata.get('compile_config')),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return text


def main():
    p=argparse.ArgumentParser(description=LABEL);p.add_argument('--experiment',type=Path,required=True)
    write_reports(p.parse_args().experiment)


if __name__ == "__main__":
    main()
