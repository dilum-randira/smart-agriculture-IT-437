"""Measured PP1 evidence and descriptive (non-causal) attention visualizations."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

from ...common.plotting import plot_experiment,PLOT_NAMES,PLOT_UNITS
from ...preprocessing.pipeline import LABEL,TARGETS,UNITS
from ...preprocessing.scaling import Standardizer
from ..lstm.reporting import markdown_table


def plots(output,history,predictions):
    plot_experiment(output,history,predictions)
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    scaler=Standardizer.from_dict(json.loads((output/'scalers_frozen.json').read_text(encoding='utf-8'))['input'])
    for s in predictions:
        node=s['node']
        with np.load(output/f'attention_{node}.npz',allow_pickle=False) as z:
            dates=pd.to_datetime(z['historical_timestamps_unix_ns'],utc=True).tz_convert('Asia/Colombo')
            weights=z['weights'][0];valid=z['history_valid_mask'][0]
            history_values=scaler.inverse_transform(z['historical_inputs_scaled'],TARGETS)[0]
        fig,axes=plt.subplots(4,1,figsize=(12,10),sharex=True)
        axes[0].plot(dates,weights,label='Normalized historical attention')
        axes[0].axhline(1/336,color='gray',linestyle=':',label='Uniform reference 1/336')
        axes[0].set_ylabel('Attention weight');axes[0].legend(fontsize=8);axes[0].grid(alpha=.2)
        for j,ax in enumerate(axes[1:]):
            ax.plot(dates,history_values[:,j],label='Historical model input')
            ax.scatter(dates[~valid],history_values[~valid,j],color='gray',s=15,label='Past-filled; original untrusted',zorder=3)
            ax.set_ylabel(f'{PLOT_NAMES[j]}\n({PLOT_UNITS[j]})');ax.grid(alpha=.2);ax.legend(fontsize=7)
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M',tz=dates.tz))
        axes[-1].set_xlabel('Historical input timestamp — Asia/Colombo; all steps at or before forecast origin')
        fig.suptitle(f'{LABEL}\n{node}: first chronological test window — descriptive attention, NOT causal explanation')
        fig.tight_layout(rect=(0,0,1,.94));fig.savefig(output/f'attention_{node}.png',dpi=140);plt.close(fig)


def write_reports(output):
    output=Path(output)
    report=json.loads((output/'training_report.json').read_text(encoding='utf-8'))
    if report['status']!='complete':raise ValueError('Training is not complete')
    metrics=pd.read_csv(output/'test_metrics.csv');comparison=pd.read_csv(output/'four_model_comparison.csv')
    current=metrics[metrics.model.eq('AttentionBiLSTM')]
    table=[[r.node,r.target,r.window_hours,r.valid_observations,f'{r.MAE:.6f}',f'{r.RMSE:.6f}',f'{r.R2:.6f}'] for r in current.itertuples()]
    winners=[[r.node,r.target,r.window_hours,f'{r.RMSE_Persistence:.6f}',f'{r.RMSE_LSTM:.6f}',f'{r.RMSE_GRU:.6f}',f'{r.RMSE_AttentionBiLSTM:.6f}',r.RMSE_winner] for r in comparison.itertuples()]
    post_path=output/'post_training_tests.json';post=json.loads(post_path.read_text(encoding='utf-8')) if post_path.exists() else 'not yet recorded'
    aggregate_path=output/'verification_summary.json';aggregate=json.loads(aggregate_path.read_text(encoding='utf-8')) if aggregate_path.exists() else 'not yet recorded'
    text=f'''# PP1 Attention BiLSTM — completed primary-model evidence

**{LABEL}**

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

Completed **{report['epochs_completed']} epochs**; selected **epoch {report['best_epoch']}**.
Fit duration **{report['training_duration_seconds']:.3f} seconds**
({report['training_duration_seconds']/60:.3f} minutes).
Selected-epoch training masked MSE **{report['best_epoch_training_loss']:.9f}**;
best validation masked MSE **{report['best_validation_loss']:.9f}**;
minimum training masked MSE **{report['minimum_training_loss']:.9f}**.
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

'''+markdown_table(['Node','Target','Cumulative hours','Valid pairs','MAE','RMSE','R²'],table)+'''

## Four-model RMSE comparison and descriptive winners

'''+markdown_table(['Node','Target','Hours','Persistence','LSTM','GRU','AttentionBiLSTM','Lowest RMSE'],winners)+f'''

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

Preflight tests: {report['preflight_tests']}. Post-training artifact tests: {post}.
Aggregate regression verification: {aggregate}.
Selected/restored model discrepancy before held-out evaluation:
{report['reload_max_absolute_error']}. Fresh-process verification separately replays
the stored test predictions and attention weights without retraining. Existing
datasets, scaler files, LSTM/GRU source/checkpoints/results remain protected by hashes.

## Reproduction (from backend)

```powershell
.\\.venv\\Scripts\\python.exe -B -u -m app.c2.microclimate.models.attention_bilstm.train --output experiments/c2/microclimate/attention_bilstm_v1_reproduction
.\\.venv\\Scripts\\python.exe -B -m app.c2.microclimate.models.attention_bilstm.verification --experiment experiments/c2/microclimate/attention_bilstm_v1
.\\.venv\\Scripts\\python.exe -B -m app.c2.microclimate.models.attention_bilstm.inference --model experiments/c2/microclimate/attention_bilstm_v1/attention_bilstm_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/attention_bilstm_v1/inference_new_NODE_01.npz
.\\.venv\\Scripts\\python.exe -B -m unittest discover -s app/c2/microclimate -t . -v
```

Training output must be new. Inference output must be a new filename inside the
chosen checkpoint directory. Verification writes logs only to this new experiment.
Artifacts include first_epoch.keras, best_validation.keras, attention_bilstm_best.keras,
frozen scaler copy, provenance, source hashes, config, architecture, history/runtime,
per-node predictions, cumulative/per-lead metrics, comparisons, forecast and
attention figures, tests and reload evidence. No baseline retraining is performed.

## Limitations and remaining PP1 tasks

{chr(10).join('- '+s for s in report['limitations'])}
- Attention weights are descriptive and not causally faithful explanations.
- A pooled R² can conceal weak node-specific skill; inspect each node and target.
- Present per-target baseline comparisons honestly, including any losses to Persistence.
- Prepare the viva demonstration and slides using these frozen artifacts; avoid tuning
  against the inspected test set. Real C1 provenance/measurement calibration and future
  independently collected field validation remain later research tasks, not PP1 evidence.
'''
    (output/'PP1_Attention_BiLSTM_Report.md').write_text(text,encoding='utf-8')
    (output/'README.md').write_text(f'# Primary Attention BiLSTM\n\n**{LABEL}**\n\nSee [executed PP1 evidence](PP1_Attention_BiLSTM_Report.md).\n',encoding='utf-8')
    return text
