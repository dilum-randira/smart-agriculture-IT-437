"""Plot clearly-labelled SYNTHETIC practice forecasts and lead-time MAE."""
import argparse
from pathlib import Path
import numpy as np
from diagnostics import lead_time_metrics, validate_forecasts

MODEL_NAMES = ("persistence", "seasonal", "lstm", "gru")


def read_practice_archive(path):
    with np.load(path, allow_pickle=False) as archive:
        required = set(MODEL_NAMES) | {"actual", "synthetic_marker", "variable"}
        if not required.issubset(archive.files):
            raise ValueError("comparison archive missing required arrays")
        if str(archive["synthetic_marker"].item()) != "SYNTHETIC_PRACTICE_ONLY":
            raise ValueError("archive must be labelled SYNTHETIC_PRACTICE_ONLY")
        if str(archive["variable"].item()) != "air_temperature_c":
            raise ValueError("unexpected target variable")
        actual = archive["actual"].copy()
        predictions = {name: archive[name].copy() for name in MODEL_NAMES}
    for predicted in predictions.values():
        validate_forecasts(actual, predicted)
    return actual, predictions


def make_plots(input_path, output_dir, example_index=0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    actual, predictions = read_practice_archive(input_path)
    if not 0 <= example_index < len(actual):
        raise ValueError("example_index out of range")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    lead_hours = np.arange(1, actual.shape[1] + 1)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(lead_hours, actual[example_index], label="Actual synthetic temperature", linewidth=2)
    for name, predicted in predictions.items():
        ax.plot(lead_hours, predicted[example_index], label=name.upper(), alpha=.85)
    ax.set(xlabel="Forecast lead (hours)", ylabel="Temperature (°C)",
           title="Synthetic Practice Only — Held-out Test Window")
    ax.grid(alpha=.3)
    ax.legend()
    fig.tight_layout()
    path1 = output_dir / "practice02_actual_vs_predicted.png"
    fig.savefig(path1, dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    for name, predicted in predictions.items():
        lead = lead_time_metrics(actual, predicted)
        ax.plot(lead["lead_hour"], lead["mae"], label=name.upper())
    ax.set(xlabel="Forecast lead (hours)", ylabel="MAE (°C)",
           title="Synthetic Practice Only — Test Error by Lead Time")
    ax.grid(alpha=.3)
    ax.legend()
    fig.tight_layout()
    path2 = output_dir / "practice02_mae_by_lead.png"
    fig.savefig(path2, dpi=140)
    plt.close(fig)
    return path1, path2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="c2/artifacts/practice02_comparison.npz")
    parser.add_argument("--output-dir", default="c2/artifacts/figures")
    parser.add_argument("--example-index", type=int, default=0)
    args = parser.parse_args()
    for path in make_plots(args.input, args.output_dir, args.example_index):
        print("Saved:", path)
