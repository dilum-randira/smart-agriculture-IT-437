"""Step 3: scale saved masked windows without regenerating or training models."""
import json
from pathlib import Path
import platform
import sys

import numpy as np
import pandas as pd

from .pipeline import Config, LABEL, TARGETS, UNITS, load, partitions, quality_valid, masked_scores
from .run_phase1 import BACKEND, SOURCE, OUTPUT as COMPLETE, digest
from .run_phase1_masked import OUTPUT as MASKED
from .scaling import fit_training_scalers

OUTPUT = BACKEND / "experiments/c2/microclimate/phase1_masked_scaled"
INVERSE_ATOL = 1e-5  # Original-unit absolute tolerance after float32 quantization.
METRIC_ATOL = 1e-5


def protected_inventory():
    paths = [SOURCE]
    for root in (COMPLETE, MASKED):
        paths.extend(sorted(p for p in root.rglob("*") if p.is_file()))
    return {p.relative_to(BACKEND).as_posix(): digest(p) for p in paths}


def check_feature_order(archive):
    if tuple(archive["features"].tolist()) != TARGETS or tuple(archive["targets"].tolist()) != TARGETS:
        raise ValueError("Saved tensor feature/target order differs from fixed contract")


def compare_metrics(frame, original, horizon_key):
    keys = ["split", "node", "target", horizon_key]
    comparison = frame.merge(original, on=keys, suffixes=("_scaled_roundtrip", "_original"), validate="one_to_one")
    if len(comparison) != len(original) or len(frame) != len(original):
        raise AssertionError("Metric row coverage changed")
    if not np.array_equal(comparison.valid_observations_scaled_roundtrip, comparison.valid_observations_original):
        raise AssertionError("Metric denominators changed")
    for metric in ("MAE", "RMSE"):
        comparison[metric+"_absolute_delta"] = np.abs(comparison[metric+"_scaled_roundtrip"]-comparison[metric+"_original"])
        if not np.allclose(comparison[metric+"_scaled_roundtrip"], comparison[metric+"_original"],
                           rtol=0, atol=METRIC_ATOL, equal_nan=True):
            raise AssertionError("Original-unit metrics failed float32 round-trip tolerance")
    comparison["evaluation_label"] = LABEL
    return comparison


def run():
    preserved = protected_inventory()
    previous = json.loads((MASKED/"validation_report.json").read_text(encoding="utf-8"))
    if digest(SOURCE) != previous["source_sha256"]:
        raise ValueError("Original synthetic CSV changed")
    data = load(SOURCE)
    config = Config()
    bounds = partitions(data, config)
    frozen = {s: dict(start=a.isoformat(), end=b.isoformat()) for s,(a,b) in bounds.items()}
    if frozen != previous["splits"]:
        raise ValueError("Frozen chronological boundaries changed")
    # Only TRAIN archive origin identifiers are consulted before fitting.
    origins = {}
    for sample in previous["samples"]:
        if sample["split"] == "train":
            with np.load(MASKED/sample["window_artifact"], allow_pickle=False) as z:
                check_feature_order(z)
                origins[sample["node"]] = z["forecast_origin_unix_ns"].copy()
    scalers, pools = fit_training_scalers(data, *bounds["train"], origins, config)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if (OUTPUT/"preservation_manifest.json").exists():
        old = json.loads((OUTPUT/"preservation_manifest.json").read_text(encoding="utf-8"))
        if old["protected_sha256"] != preserved:
            raise ValueError("Protected original artifacts changed since first scaled run")
    scaler_record = dict(evaluation_label=LABEL, method="per-feature population standardization (ddof=0)",
                         node_policy="shared across nodes; each node/timestamp observation weighted once",
                         input=scalers["input"].to_dict(), target=scalers["target"].to_dict(),
                         units=dict(zip(TARGETS, UNITS)), zero_variance_policy="scale=1 for zero/numerically constant features",
                         masked_target_placeholder="float32 0 in standardized space, mask=False; never ground truth")
    (OUTPUT/"scalers.json").write_text(json.dumps(scaler_record, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    fit_pools = {}
    for role, table in pools.items():
        name = f"{role}_scaler_fit_observations.csv"
        table.assign(evaluation_label=LABEL).to_csv(OUTPUT/name, index=False)
        fit_pools[role] = dict(rows=len(table), per_node=table.node_id.value_counts().to_dict(),
                               start=table.timestamp.min().isoformat(), end=table.timestamp.max().isoformat(),
                               artifact=name, artifact_sha256=digest(OUTPUT/name))
    report = dict(evaluation_label=LABEL, experiment="phase1_masked_scaled", source_sha256=digest(SOURCE),
                  splits=frozen, config=previous["config"], target_eligibility=previous["eligibility"],
                  features=list(TARGETS), targets=list(TARGETS), scalers=scaler_record, fit_pools=fit_pools,
                  fit_policy="Separate input/target pools: unique original (node_id,timestamp) rows used by retained "
                             "training histories/targets; only quality-eligible rows before any forward filling. "
                             "No flattened-window fitting, validation/test fit, or boundary-crossing target observations.",
                  mask_policy="Preserved byte-for-byte array values/dtypes. Future target masks are supervision only.",
                  transform_policy="X: standardize existing causal histories. y: select valid cells before arithmetic; "
                                   "masked-out values become finite standardized zero placeholders, always loss-masked.",
                  inverse_policy="Predictions use target scaler inverse; actual masked targets return NaN where mask=False. "
                                 "Persistence bridges inverse(input) -> target transform -> inverse(target).",
                  training="None. No neural networks or new data integration.", python=platform.python_version(),
                  interpreter=sys.executable, numpy=np.__version__, pandas=pd.__version__,
                  inverse_absolute_tolerance=INVERSE_ATOL, metric_absolute_tolerance=METRIC_ATOL,
                  code_sha256={p.name:digest(p) for p in Path(__file__).parent.glob("*.py")}, samples=[])
    rows, leads = [], []
    for sample in previous["samples"]:
        split, node = sample["split"], sample["node"]
        with np.load(MASKED/sample["window_artifact"], allow_pickle=False) as z:
            check_feature_order(z)
            raw_x, raw_y = z["X"], z["y"]
            mask, history_mask = z["target_valid_mask"], z["history_valid_mask"]
            stamps = z["forecast_origin_unix_ns"]
            if mask.dtype != np.bool_ or history_mask.dtype != np.bool_:
                raise ValueError("Expected original boolean observation masks")
            times = pd.to_datetime(stamps, utc=True).tz_convert("Asia/Colombo")
            start, end = bounds[split]
            assert (times-pd.Timedelta(hours=335) >= start).all()
            assert (times+pd.Timedelta(hours=168) <= end).all()
            # Verify that the inherited masks mean original source quality, not filled data.
            part = data[data.node_id.eq(node) & data.timestamp.between(start,end)].reset_index(drop=True)
            positions = pd.DatetimeIndex(part.timestamp).get_indexer(times)
            if (positions < 335).any():
                raise ValueError("Saved sample origins not aligned with source node/partition")
            valid = quality_valid(part).to_numpy()
            hidx = positions[:,None]+np.arange(-335,1)
            tidx = positions[:,None]+np.arange(1,169)
            assert np.array_equal(history_mask, valid[hidx])
            assert np.array_equal(mask, np.repeat(valid[tidx][...,None],3,axis=2))
            assert np.array_equal(raw_y, part.loc[:,TARGETS].to_numpy()[tidx])
            x = scalers["input"].transform(raw_x, TARGETS)
            y = scalers["target"].transform_targets(raw_y, mask, TARGETS)
            assert x.dtype == y.dtype == np.float32
            assert x.shape == raw_x.shape and y.shape == raw_y.shape
            assert np.isfinite(x).all() and np.isfinite(y).all() and (y[~mask] == 0).all()
            restored_x = scalers["input"].inverse_transform(x, TARGETS)
            restored_y = scalers["target"].inverse_targets(y, mask, TARGETS)
            x_error = np.max(np.abs(restored_x-raw_x), axis=(0,1))
            y_error = [float(np.abs(restored_y[...,j][mask[...,j]]-raw_y[...,j][mask[...,j]]).max()) for j in range(3)]
            assert max(x_error) <= INVERSE_ATOL and max(y_error) <= INVERSE_ATOL
            physical_persistence = np.repeat(restored_x[:,-1:,:],168,axis=1)
            target_space_prediction = scalers["target"].transform(physical_persistence, TARGETS)
            restored_prediction = scalers["target"].inverse_transform(target_space_prediction, TARGETS)
            metrics, lead_metrics = masked_scores(restored_y, restored_prediction, mask)
            rows.extend(dict(split=split,node=node,**r) for r in metrics)
            leads.extend(dict(split=split,node=node,**r) for r in lead_metrics)
            payload = {key:z[key].copy() for key in z.files if key not in {"X","y"}}
            np.savez_compressed(OUTPUT/sample["window_artifact"], **payload, X=x, y=y,
                                scaler_parameters_sha256=np.array(digest(OUTPUT/"scalers.json")),
                                target_placeholder=np.array("standardized zero; excluded by target_valid_mask"))
            report["samples"].append(dict(split=split,node=node,window_artifact=sample["window_artifact"],
                                          input_shape=list(x.shape), output_shape=list(y.shape), dtype="float32",
                                          target_mask_shape=list(mask.shape), history_mask_shape=list(history_mask.shape),
                                          valid_target_counts_per_feature=mask.sum(axis=(0,1)).tolist(),
                                          valid_history_observations=int(history_mask.sum()),
                                          masked_target_placeholders=int((~mask).sum()),
                                          input_inverse_max_absolute_error=x_error.tolist(),
                                          target_inverse_max_absolute_error=y_error))
    frame, lead_frame = pd.DataFrame(rows), pd.DataFrame(leads)
    comparisons = compare_metrics(frame, pd.read_csv(MASKED/"persistence_metrics.csv"), "window_hours")
    lead_comparisons = compare_metrics(lead_frame, pd.read_csv(MASKED/"persistence_lead_time_metrics.csv"), "lead_hour")
    frame.to_csv(OUTPUT/"original_unit_persistence_metrics.csv", index=False)
    lead_frame.to_csv(OUTPUT/"original_unit_persistence_lead_time_metrics.csv", index=False)
    comparisons.to_csv(OUTPUT/"metric_roundtrip_comparison.csv", index=False)
    report["metric_verification"] = dict(cumulative_rows=len(frame), lead_rows=len(lead_frame),
                                         cumulative_max_MAE_delta=float(comparisons.MAE_absolute_delta.max()),
                                         cumulative_max_RMSE_delta=float(comparisons.RMSE_absolute_delta.max()),
                                         lead_max_MAE_delta=float(lead_comparisons.MAE_absolute_delta.max()),
                                         lead_max_RMSE_delta=float(lead_comparisons.RMSE_absolute_delta.max()))
    # Copy alignment evidence, not regenerate windows/splits or touch the upstream manifest.
    (OUTPUT/"sample_manifest.csv").write_bytes((MASKED/"sample_manifest.csv").read_bytes())
    if protected_inventory() != preserved:
        raise AssertionError("Original CSV or unscaled experiment artifacts changed")
    report["preserved_file_count"] = len(preserved)
    preservation = dict(evaluation_label=LABEL, protected_sha256=preserved, unchanged_after_execution=True)
    for name, content in [("validation_report.json",report),("preservation_manifest.json",preservation)]:
        (OUTPUT/name).write_text(json.dumps(content,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    summary = [LABEL, "", "Train-only standardization; no model training. Target masks remain mandatory.",
               "Shared across nodes, unique genuine training timestamps per scaler role.", "",
               json.dumps(scaler_record,indent=2,ensure_ascii=False), "",
               pd.DataFrame(report["samples"])[["split","node","input_shape","output_shape","dtype","valid_target_counts_per_feature"]].to_string(index=False),
               "", json.dumps(report["metric_verification"],indent=2)]
    (OUTPUT/"summary.txt").write_text("\n".join(summary)+"\n",encoding="utf-8")
    print("\n".join(summary))
    print("Evidence:",OUTPUT)
    return report


def main():
    import argparse
    argparse.ArgumentParser(description=LABEL).parse_args()
    run()


if __name__ == "__main__":
    main()
