"""Run from backend: python -B -m app.c2.microclimate.preprocessing.run_phase1."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

import numpy as np
import pandas as pd

from .pipeline import (Config, EXCLUDED, FUTURE_FEATURE_CONTRACT, LABEL, TARGETS,
                       UNITS, load, partitions, persistence, quality_valid, scores, windows)

from ..common.paths import BACKEND, SOURCE, OUTPUT, digest


def make_plot(y, prediction, origins, split, node, output, target_valid_mask=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    if not len(y):
        return None
    # Deterministic first eligible origin; no selection using forecast error.
    dates = pd.date_range(origins[0]+pd.Timedelta(hours=1), periods=y.shape[1], freq="h")
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    for j, ax in enumerate(axes):
        actual = y[0, :, j] if target_valid_mask is None else np.where(target_valid_mask[0, :, j], y[0, :, j], np.nan)
        ax.plot(dates, actual, label="Eligible synthetic target (gaps = masked)" if target_valid_mask is not None else "Actual synthetic target", linewidth=1.4)
        ax.plot(dates, prediction[0, :, j], label="Persistence", linestyle="--")
        ax.set_ylabel(f"{TARGETS[j]}\n({UNITS[j]})")
        ax.grid(alpha=.25)
        ax.legend(loc="upper right")
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M", tz=dates.tz))
    axes[-1].set_xlabel("Forecast target time — Asia/Colombo (UTC+05:30)")
    fig.suptitle(f"{LABEL}\n{node} · {split} · issued {origins[0].isoformat()}")
    fig.tight_layout(rect=(0, 0, 1, .94))
    filename = f"actual_vs_persistence_{split}_{node}.png"
    fig.savefig(output / filename, dpi=140)
    plt.close(fig)
    return filename


def lead_plot(table, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    for j, ax in enumerate(axes):
        for (split, node), group in table[table.target.eq(TARGETS[j]) & table.samples.gt(0)].groupby(["split", "node"]):
            ax.plot(group.lead_hour, group.MAE, label=f"{split} / {node}")
        ax.set_ylabel(f"MAE ({UNITS[j]})")
        ax.grid(alpha=.25)
        ax.legend(fontsize=8)
    axes[-1].set_xlabel("Forecast lead (hours after issue time)")
    fig.suptitle(f"{LABEL}\nPersistence lead-time error; overlapping forecast origins")
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(output / "lead_time_mae.png", dpi=140)
    plt.close(fig)


def run(config=Config(), output=OUTPUT):
    output = Path(output).resolve()
    # This entry point writes evidence only inside the C2 experiment directory.
    if not output.is_relative_to((BACKEND / "experiments/c2/microclimate").resolve()):
        raise ValueError("Output must stay in experiments/c2/microclimate")
    source_hash = digest(SOURCE)
    raw = pd.read_csv(SOURCE)
    d = load(SOURCE)
    if len(d) != 17520 or set(d.node_id) != {"NODE_01", "NODE_02"}:
        raise ValueError("Unexpected proposal input dataset size/nodes")
    bounds = partitions(d, config)
    output.mkdir(parents=True, exist_ok=True)
    report = dict(evaluation_label=LABEL, source=str(SOURCE.relative_to(BACKEND)), source_sha256=source_hash,
                  config=vars(config), features=list(TARGETS), targets=list(TARGETS), excluded_fields=list(EXCLUDED),
                  future_feature_contract=FUTURE_FEATURE_CONTRACT,
                  rows=len(d), columns=len(d.columns), origin_counts=d.data_origin.value_counts().to_dict(),
                  missing_counts=raw.isna().sum().to_dict(), duplicate_keys=0, hourly_gaps=0,
                  status_counts=d.record_status.value_counts().to_dict(), anomaly_rows=int(d.is_anomaly.sum()),
                  imputed_rows=int(d.is_imputed.sum()), imputed_fields=d.imputed_fields.value_counts().to_dict(),
                  usable_rows=int(quality_valid(d).sum()),
                  warn_usable_rows=int((d.record_status.eq("WARN") & quality_valid(d)).sum()),
                  quality_score_range=[float(d.quality_score.min()), float(d.quality_score.max())],
                  splits={s: {"start": a.isoformat(), "end": b.isoformat()} for s, (a,b) in bounds.items()},
                  python=platform.python_version(), interpreter=sys.executable,
                  packages={p: importlib.metadata.version(p) for p in ("numpy", "pandas", "matplotlib")},
                  code_sha256={p.name: digest(p) for p in Path(__file__).parent.glob("*.py")},
                  quality_policy="INVALID/anomalous/imputed rows masked as history; causal split-local forward fill only. "
                                 "All target steps must be unflagged, non-INVALID observations. No target imputation.",
                  preprocessing_fit="None: no scaling, learned imputation, training, or fitted preprocessing.",
                  window_policy="Inputs and all targets entirely within one node and partition; stride in hours.",
                  limitations=["Entirely synthetic; no field accuracy evidence.",
                               "Complete-label filtering can leave node/partition combinations with zero samples.",
                               "Hourly rolling windows overlap; counts are not independent observations.",
                               "Historical gap fills may be stale; masks are saved for Phase 2.",
                               "No growth-stage inputs or verified forecast-weather issue times; external datasets unused."],
                  node_validation={node: dict(rows=len(g), start=g.timestamp.min().isoformat(),
                                             end=g.timestamp.max().isoformat(), zone=g.zone_id.iloc[0],
                                             status_counts=g.record_status.value_counts().to_dict(),
                                             anomaly_rows=int(g.is_anomaly.sum()),imputed_rows=int(g.is_imputed.sum()),
                                             usable_rows=int(quality_valid(g).sum()))
                                   for node,g in d.groupby("node_id")},
                  samples=[])
    metrics, leads, origins_rows = [], [], []
    for split, (start, end) in bounds.items():
        for node, group in d.groupby("node_id", sort=True):
            part = group[group.timestamp.between(start,end)].reset_index(drop=True)
            x,y,origins,candidates = windows(part,config)
            pred = persistence(x,config.horizon)
            assert pred.shape == y.shape
            if origins:
                assert origins[0] - pd.Timedelta(hours=config.lookback-1) >= start
                assert origins[-1] + pd.Timedelta(hours=config.horizon) <= end
            quality = quality_valid(part).to_numpy()
            times = pd.DatetimeIndex(part.timestamp)
            positions = [times.get_loc(t) for t in origins]
            history_masks = np.array([quality[t-config.lookback+1:t+1] for t in positions],dtype=bool).reshape(-1,config.lookback)
            filename = f"windows_{split}_{node}.npz"
            np.savez_compressed(output / filename, X=x, y=y, history_valid_mask=history_masks,
                                forecast_origin_unix_ns=np.array([t.value for t in origins],dtype=np.int64),
                                evaluation_label=np.array(LABEL), features=np.array(TARGETS),
                                targets=np.array(TARGETS), timezone=np.array("Asia/Colombo"))
            rows, lead_rows = scores(y,pred)
            for row in rows:
                metrics.append(dict(split=split,node=node,**row))
            for row in lead_rows:
                leads.append(dict(split=split,node=node,**row))
            for i, t in enumerate(origins):
                origins_rows.append(dict(split=split,node=node,sample=i,input_start=(t-pd.Timedelta(hours=config.lookback-1)).isoformat(),
                                         origin=t.isoformat(),target_start=(t+pd.Timedelta(hours=1)).isoformat(),
                                         target_end=(t+pd.Timedelta(hours=config.horizon)).isoformat(),evaluation_label=LABEL))
            sample=dict(split=split,node=node,rows=len(part),quality_usable_rows=int(quality.sum()),
                        candidate_windows=candidates,valid_samples=len(y),rejected_windows=candidates-len(y),
                        input_shape=list(x.shape),output_shape=list(y.shape),window_artifact=filename,
                        plot=make_plot(y,pred,origins,split,node,output))
            report["samples"].append(sample)
    metrics_df=pd.DataFrame(metrics)
    leads_df=pd.DataFrame(leads)
    metrics_df.to_csv(output/"persistence_metrics.csv",index=False)
    leads_df.to_csv(output/"persistence_lead_time_metrics.csv",index=False)
    pd.DataFrame(origins_rows).to_csv(output/"sample_manifest.csv",index=False)
    lead_plot(leads_df,output)
    assert digest(SOURCE)==source_hash, "Original CSV changed"
    (output/"validation_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    text = [f"# {LABEL}", "", "Persistence: repeat last valid historical target for every future hour.",
            "No model training or fitted preprocessing. Missing metrics mean zero eligible windows, not zero error.", "",
            metrics_df.to_string(index=False), "", "Window counts/shapes:",
            pd.DataFrame(report["samples"]).drop(columns=["plot"]).to_string(index=False)]
    (output/"summary.txt").write_text("\n".join(text)+"\n",encoding="utf-8")
    print(LABEL)
    print(pd.DataFrame(report["samples"])[["split","node","valid_samples","input_shape","output_shape"]].to_string(index=False))
    print(metrics_df.drop(columns=["evaluation_label"]).to_string(index=False))
    print("Evidence:", output)
    return report


def main():
    parser=argparse.ArgumentParser(description=LABEL)
    parser.add_argument("--lookback",type=int,default=336)
    parser.add_argument("--horizon",type=int,default=168)
    parser.add_argument("--stride",type=int,default=1)
    parser.add_argument("--train-fraction",type=float,default=.70)
    parser.add_argument("--validation-fraction",type=float,default=.15)
    parser.add_argument("--output",type=Path,default=OUTPUT)
    args=parser.parse_args()
    run(Config(args.lookback,args.horizon,args.train_fraction,args.validation_fraction,args.stride),args.output)


if __name__ == "__main__":
    main()
