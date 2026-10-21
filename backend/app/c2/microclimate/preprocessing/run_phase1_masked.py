"""Versioned target-masked evaluation; original phase1 evidence is read-only."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

import numpy as np
import pandas as pd

from .pipeline import (Config, LABEL, TARGETS, EXCLUDED, load, partitions,
                       quality_valid, masked_windows, masked_scores, persistence)
from .run_phase1 import BACKEND, SOURCE, OUTPUT as ORIGINAL, digest, make_plot, lead_plot

OUTPUT = BACKEND / "experiments/c2/microclimate/phase1_masked"
MINIMUM_TARGET_FRACTION = .95


def protected_inventory():
    paths = [SOURCE, *sorted(p for p in ORIGINAL.rglob("*") if p.is_file())]
    return {p.relative_to(BACKEND).as_posix(): digest(p) for p in paths}


def training_quality(data, bounds, config):
    """Descriptive training-only quality analysis, never prediction-error tuning."""
    start, end = bounds["train"]
    records = []
    minimum = int(np.ceil(MINIMUM_TARGET_FRACTION * config.horizon))
    for node, group in data.groupby("node_id"):
        part = group[group.timestamp.between(start, end)]
        valid = quality_valid(part).to_numpy()
        counts = np.array([valid[t:t+config.horizon].sum()
                           for t in range(config.lookback, len(part)-config.horizon+1)])
        values, frequencies = np.unique(counts, return_counts=True)
        records.append(dict(node=node, candidates=len(counts), minimum_valid_hours=int(counts.min()),
                            median_valid_hours=float(np.median(counts)), maximum_valid_hours=int(counts.max()),
                            valid_hours_distribution={str(v): int(n) for v, n in zip(values, frequencies)},
                            target_hours_required=minimum, meeting_coverage_rule=int((counts >= minimum).sum())))
    return dict(evaluation_label=LABEL, analysis_partition="train only", nodes=records,
                minimum_target_fraction=MINIMUM_TARGET_FRACTION, minimum_valid_hours_per_target=minimum,
                rationale="Training medians are 165/168; requiring >=95% (160/168) usable hours retains "
                          "most training windows while excluding its lower-coverage tail. Fixed before "
                          "validation/test evaluation; not optimized using forecast errors.")


def run():
    protected = protected_inventory()
    previous = json.loads((ORIGINAL / "validation_report.json").read_text(encoding="utf-8"))
    if digest(SOURCE) != previous["source_sha256"]:
        raise ValueError("Source differs from frozen complete-case experiment")
    config = Config()
    data = load(SOURCE)
    bounds = partitions(data, config)
    serialized_bounds = {s: dict(start=a.isoformat(), end=b.isoformat()) for s, (a,b) in bounds.items()}
    if serialized_bounds != previous["splits"]:
        raise ValueError("Frozen chronological boundaries changed")
    development = training_quality(data, bounds, config)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if (OUTPUT / "preservation_manifest.json").exists():
        saved = json.loads((OUTPUT / "preservation_manifest.json").read_text(encoding="utf-8"))
        if saved["protected_sha256"] != protected:
            raise ValueError("Protected original artifacts changed since first masked run")
    report = dict(evaluation_label=LABEL, experiment="phase1_masked", config=vars(config),
                  source=SOURCE.relative_to(BACKEND).as_posix(), source_sha256=digest(SOURCE),
                  splits=serialized_bounds, features=list(TARGETS), targets=list(TARGETS),
                  excluded_fields=list(EXCLUDED), eligibility=development,
                  target_policy="Boolean original-row quality, repeated across all three channels. "
                                "INVALID OR anomaly OR supplied-imputed => False. Clean WARN is eligible. "
                                "Computed before historical forward filling; y contains unchanged source "
                                "values, including untrusted values at mask=False. Always use the mask.",
                  input_policy="Unchanged causal split-local forward fill; finite 336-hour history required.",
                  preprocessing_fit="None: no input or target scaling, model fitting or training.",
                  metrics_policy="Select eligible cells before error arithmetic; normalize by valid observations. "
                                 "Zero denominator => unavailable (None/blank CSV).",
                  python=platform.python_version(), interpreter=sys.executable,
                  packages={p: importlib.metadata.version(p) for p in ("numpy", "pandas", "matplotlib")},
                  code_sha256={p.name: digest(p) for p in Path(__file__).parent.glob("*.py")},
                  limitations=["100% synthetic; no field-accuracy evidence.",
                               "Overlapping forecasts repeat target observations; counts are not independent.",
                               "Quality flags can cause selection bias; the 95% floor is an operational policy, not a proven optimum.",
                               "Future target masks are labels/loss metadata, never model inputs.",
                               "Differentiable masked-loss integration is Phase 2; NumPy reference loss only here.",
                               "No scaling, external climate integration or growth-stage fabrication."], samples=[])
    metric_rows, lead_rows, manifest_rows = [], [], []
    for split, (start, end) in bounds.items():
        for node, group in data.groupby("node_id", sort=True):
            part = group[group.timestamp.between(start, end)].reset_index(drop=True)
            x, y, mask, origins, candidates = masked_windows(part, config, MINIMUM_TARGET_FRACTION)
            assert mask.shape == y.shape == (len(origins), 168, 3)
            assert x.shape == (len(origins), 336, 3)
            valid = quality_valid(part).to_numpy()
            times = pd.DatetimeIndex(part.timestamp)
            positions = times.get_indexer(origins)
            history_mask = np.array([valid[t-335:t+1] for t in positions], dtype=bool).reshape(-1, 336)
            unique_eligible_times = np.zeros((len(part), 3), dtype=bool)
            for i, t in enumerate(positions):
                assert origins[i]-pd.Timedelta(hours=335) >= start
                assert origins[i]+pd.Timedelta(hours=168) <= end
                expected = np.repeat(valid[t+1:t+169, None], 3, axis=1)
                assert np.array_equal(mask[i], expected)
                unique_eligible_times[t+1:t+169] |= mask[i]
                manifest_rows.append(dict(split=split, node=node, sample=i,
                                          input_start=(origins[i]-pd.Timedelta(hours=335)).isoformat(),
                                          origin=origins[i].isoformat(),
                                          target_start=(origins[i]+pd.Timedelta(hours=1)).isoformat(),
                                          target_end=(origins[i]+pd.Timedelta(hours=168)).isoformat(),
                                          valid_hours_per_target=int(mask[i, :, 0].sum()), evaluation_label=LABEL))
            filename = f"windows_{split}_{node}.npz"
            np.savez_compressed(OUTPUT/filename, X=x, y=y, target_valid_mask=mask,
                                history_valid_mask=history_mask,
                                forecast_origin_unix_ns=np.array([t.value for t in origins], dtype=np.int64),
                                features=np.array(TARGETS), targets=np.array(TARGETS),
                                timezone=np.array("Asia/Colombo"), evaluation_label=np.array(LABEL),
                                minimum_target_fraction=np.array(MINIMUM_TARGET_FRACTION))
            prediction = persistence(x, config.horizon)
            rows, leads = masked_scores(y, prediction, mask)
            metric_rows.extend(dict(split=split, node=node, **r) for r in rows)
            lead_rows.extend(dict(split=split, node=node, **r) for r in leads)
            sample = dict(split=split, node=node, candidate_windows=candidates, eligible_samples=len(y),
                          rejected_windows=candidates-len(y), input_shape=list(x.shape), output_shape=list(y.shape),
                          mask_shape=list(mask.shape), target_mask_dtype=str(mask.dtype),
                          valid_observations_per_target=dict(zip(TARGETS, mask.sum(axis=(0,1)).tolist())),
                          unique_valid_target_timestamps_per_target=dict(zip(TARGETS, unique_eligible_times.sum(axis=0).tolist())),
                          possible_observations_per_target=len(y)*168,
                          window_artifact=filename,
                          plot=make_plot(y, prediction, origins, split, node, OUTPUT, mask))
            report["samples"].append(sample)
    metrics = pd.DataFrame(metric_rows)
    leads = pd.DataFrame(lead_rows)
    metrics.to_csv(OUTPUT/"persistence_metrics.csv", index=False)
    leads.to_csv(OUTPUT/"persistence_lead_time_metrics.csv", index=False)
    pd.DataFrame(manifest_rows).to_csv(OUTPUT/"sample_manifest.csv", index=False)
    lead_plot(leads, OUTPUT)
    if protected_inventory() != protected:
        raise AssertionError("Original CSV/phase1 artifacts changed")
    preservation = dict(evaluation_label=LABEL, protected_sha256=protected, unchanged_after_execution=True)
    for filename, content in [("validation_report.json", report), ("development_quality.json", development),
                              ("preservation_manifest.json", preservation)]:
        (OUTPUT/filename).write_text(json.dumps(content, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    summary = [LABEL, "", "Target masks are mandatory. Original-unit y is unchanged; mask=False is NOT ground truth.",
               "No scaling or training. Counts include repeated target timestamps across rolling forecasts.", "",
               pd.DataFrame(report["samples"])[["split", "node", "eligible_samples", "rejected_windows", "input_shape", "output_shape", "mask_shape"]].to_string(index=False),
               "", metrics.drop(columns="evaluation_label").to_string(index=False)]
    (OUTPUT/"summary.txt").write_text("\n".join(summary)+"\n", encoding="utf-8")
    print("\n".join(summary))
    print("Evidence:", OUTPUT)
    return report


def main():
    import argparse
    argparse.ArgumentParser(description=LABEL).parse_args()
    run()


if __name__ == "__main__":
    main()
