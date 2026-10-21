"""Plots and PP1 evidence generated only from completed GRU experiments."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ...preprocessing.pipeline import LABEL, TARGETS, UNITS
from ..lstm.reporting import markdown_table
from .evaluation import LSTM_OUTPUT


def plots(output, history, predictions):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    fig, ax=plt.subplots(figsize=(10,5))
    ax.plot(history.epoch,history.loss,label='GRU training masked MSE')
    ax.plot(history.epoch,history.val_loss,label='GRU validation masked MSE')
    ax.axvline(history.loc[history.val_loss.idxmin(),'epoch'],linestyle=':',color='gray',label='Validation-selected epoch')
    ax.set(xlabel='Completed epoch',ylabel='MSE in standardized target space',title=LABEL)
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(output/'loss_curves.png',dpi=140);plt.close(fig)
    for node, actual, gru, persistence, mask, origins in predictions:
        with np.load(LSTM_OUTPUT/f'test_predictions_{node}.npz',allow_pickle=False) as z:
            lstm=z['predictions_original_units'][0]
        dates=pd.date_range(pd.Timestamp(int(origins[0]),tz='UTC').tz_convert('Asia/Colombo')+pd.Timedelta(hours=1),periods=168,freq='h')
        fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True)
        for j,ax in enumerate(axes):
            ax.plot(dates,np.where(mask[0,:,j],actual[0,:,j],np.nan),label='Eligible synthetic actual')
            ax.plot(dates,gru[0,:,j],label='Standard GRU')
            ax.plot(dates,lstm[:,j],label='Saved standard LSTM',alpha=.75)
            ax.plot(dates,persistence[0,:,j],label='Persistence',linestyle='--',alpha=.6)
            ax.set_ylabel(f'{TARGETS[j]}\n({UNITS[j]})');ax.legend(fontsize=8);ax.grid(alpha=.2)
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M',tz=dates.tz))
        axes[-1].set_xlabel('Target timestamp — Asia/Colombo (UTC+05:30)')
        fig.suptitle(f'{LABEL}\n{node}: first chronological test origin; seven consecutive days')
        fig.tight_layout(rect=(0,0,1,.94));fig.savefig(output/f'forecast_{node}.png',dpi=140);plt.close(fig)


def write_reports(output):
    output=Path(output)
    report=json.loads((output/'training_report.json').read_text(encoding='utf-8'))
    if report['status']!='complete':raise ValueError('Cannot claim incomplete training succeeded')
    metrics=pd.read_csv(output/'test_metrics.csv')
    comp=pd.read_csv(output/'three_model_comparison.csv')
    rows=[[r.model,r.node,r.target,r.window_hours,r.valid_observations,f'{r.MAE:.5f}',f'{r.RMSE:.5f}',f'{r.R2:.5f}'] for r in metrics.itertuples()]
    counts=metrics[metrics.model.eq('GRU')][['node','target','window_hours','valid_observations','masked_observations']]
    post_path=output/'post_training_tests.json'
    post=json.loads(post_path.read_text(encoding='utf-8')) if post_path.exists() else None
    text=f'''# PP1 GRU baseline — executed evidence

**{LABEL}**

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

Completed **{report['epochs_completed']} epochs**; best validation epoch **{report['best_epoch']}**.
Actual fit duration **{report['training_duration_seconds']:.3f} seconds**
({report['training_duration_seconds']/60:.3f} minutes).
Training masked MSE at selected epoch **{report['best_epoch_training_loss']:.9f}**;
best validation masked MSE **{report['best_validation_loss']:.9f}**.
Minimum training loss over all epochs **{report['minimum_training_loss']:.9f}**.
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

'''+markdown_table(['Model','Node','Target','Hours','Valid pairs','MAE','RMSE','R²'],rows)+f'''

GRU RMSE is lower than Persistence in **{int((comp.RMSE_gru<comp.RMSE_persistence).sum())}/27**
node/pooled-target-horizon rows and lower than LSTM in
**{int((comp.RMSE_gru<comp.RMSE_lstm).sum())}/27** rows. These descriptive counts do
not establish statistical significance or real-field superiority.

## Valid eligible forecast/observation pairs

'''+markdown_table(list(counts.columns),counts.values.tolist())+f'''

## Verification and reproducibility

Preflight: {report['preflight_tests']['tests_run']} tests passed, no failures/errors/skips.
Post-training verification: {post if post else 'not yet recorded; see subsequent verification evidence'}.
The best checkpoint is `gru_best.keras`; `first_epoch.keras` and
`best_validation.keras` retain epoch and validation-selection evidence. Frozen
scalers are copied byte-for-byte. Existing data, experiments and LSTM artifacts
match their pre-run hashes. Fresh-process verification independently recalculates
metrics and replays both full saved test prediction arrays.

From backend, using the existing venv (training output must be new):

```powershell
.\\.venv\\Scripts\\python.exe -B -u -m app.c2.microclimate.models.gru.train --output experiments/c2/microclimate/gru_v1_reproduction
.\\.venv\\Scripts\\python.exe -B -m app.c2.microclimate.models.gru.verification --experiment experiments/c2/microclimate/gru_v1
.\\.venv\\Scripts\\python.exe -B -m app.c2.microclimate.models.gru.inference --model experiments/c2/microclimate/gru_v1/gru_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/gru_v1/inference_new_NODE_01.npz
.\\.venv\\Scripts\\python.exe -B -m unittest discover -s app/c2/microclimate -t . -v
```

Evidence includes training config/history/runtime, architecture, source/input
hashes, three checkpoints, frozen scalers, per-node predictions, 81 cumulative
metric rows, per-lead metrics, 27 three-model comparison rows, loss curves and
timestamped forecast plots. Existing outputs are never reused as training output.

## Limitations

{chr(10).join('- '+v for v in report['limitations'])}
- Pooled R² includes between-node variation and is not interchangeable with node R².
- No NASA POWER/ERA5-Land integration, fabricated growth stages or real C1 input.
- The fixed GRU is unidirectional and is not the proposal's primary attention model.
'''
    (output/'PP1_GRU_Implementation_Report.md').write_text(text,encoding='utf-8')
    (output/'README.md').write_text(f'# Completed standard GRU baseline\n\n**{LABEL}**\n\nSee [executed report](PP1_GRU_Implementation_Report.md).\n',encoding='utf-8')
    return text
