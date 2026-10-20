
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BACKEND = Path(__file__).resolve().parents[3]
RESULT_DIR = BACKEND / "experiments/c2/yield"


def generate_plots():
    metrics = pd.read_csv(
        RESULT_DIR / "yield_final_test_metrics.csv"
    )

    predictions = pd.read_csv(
        RESULT_DIR / "yield_final_test_predictions.csv"
    )

    # Plot 1: Model comparison
    metrics = metrics.sort_values("MAE_g_per_plant")

    plt.figure(figsize=(9, 5))
    plt.bar(
        metrics["model"],
        metrics["MAE_g_per_plant"]
    )
    plt.ylabel("MAE (g/plant)")
    plt.title("Yield Prediction - Final Test Comparison")
    plt.xticks(rotation=15)
    plt.tight_layout()

    plt.savefig(
        RESULT_DIR / "final_model_comparison.png",
        dpi=200
    )
    plt.close()

    # Plot 2: XGBoost actual vs predicted
    xgb = predictions[
        predictions["model"] == "Tuned XGBoost"
    ]

    plt.figure(figsize=(7, 6))
    plt.scatter(
        xgb["actual_yield_g"],
        xgb["predicted_yield_g"],
        alpha=0.7
    )

    minimum = min(
        xgb["actual_yield_g"].min(),
        xgb["predicted_yield_g"].min()
    )

    maximum = max(
        xgb["actual_yield_g"].max(),
        xgb["predicted_yield_g"].max()
    )

    plt.plot(
        [minimum, maximum],
        [minimum, maximum],
        linestyle="--",
        label="Perfect prediction"
    )

    plt.xlabel("Actual yield (g/plant)")
    plt.ylabel("Predicted yield (g/plant)")
    plt.title("Tuned XGBoost - Held-out Test")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        RESULT_DIR / "xgboost_actual_vs_predicted.png",
        dpi=200
    )
    plt.close()

    print("Both evaluation graphs saved successfully.")


if __name__ == "__main__":
    generate_plots()
