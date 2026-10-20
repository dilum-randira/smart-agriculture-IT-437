
from pathlib import Path

import joblib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

from .training import FEATURES


BACKEND = Path(__file__).resolve().parents[3]

DATA_FILE = (
    BACKEND / "data/c2/yield/processed"
    / "peerj_development.csv"
)

MODEL_FILE = (
    BACKEND / "models/c2/yield"
    / "xgboost_tuned_development.joblib"
)

RESULT_DIR = BACKEND / "experiments/c2/yield"


def generate_shap_explanations():
    print("Loading development dataset...")
    df = pd.read_csv(DATA_FILE)

    print("Loading trained XGBoost model...")
    pipeline = joblib.load(MODEL_FILE)

    # Use the same preprocessing fitted during training
    X = df[FEATURES].apply(
        pd.to_numeric, errors="coerce"
    )

    imputer = pipeline.named_steps["imputer"]
    xgb_model = pipeline.named_steps["model"]

    X_processed = pd.DataFrame(
        imputer.transform(X),
        columns=FEATURES,
        index=X.index,
    )

    print("Calculating SHAP values...")
    explainer = shap.TreeExplainer(xgb_model)
    shap_values = explainer(X_processed)

    RESULT_DIR.mkdir(
        parents=True, exist_ok=True
    )

    # 1. Global feature importance
    plt.figure()
    shap.plots.bar(shap_values, show=False)
    plt.title("XGBoost - SHAP Feature Importance")
    plt.tight_layout()
    plt.savefig(
        RESULT_DIR / "shap_feature_importance.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close("all")

    # 2. Feature impact and direction
    plt.figure()
    shap.plots.beeswarm(shap_values, show=False)
    plt.title("XGBoost - SHAP Summary")
    plt.tight_layout()
    plt.savefig(
        RESULT_DIR / "shap_summary_beeswarm.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close("all")

    # 3. Numerical feature importance
    importance = pd.DataFrame({
        "feature": FEATURES,
        "mean_absolute_shap": (
            abs(shap_values.values).mean(axis=0)
        ),
    })

    importance = importance.sort_values(
        "mean_absolute_shap",
        ascending=False,
    )

    importance.to_csv(
        RESULT_DIR / "shap_feature_importance.csv",
        index=False,
    )

    print("\n===== SHAP FEATURE IMPORTANCE =====")
    print(importance.to_string(index=False))

    print("\nSHAP analysis completed!")
    print("Saved results to:", RESULT_DIR)


if __name__ == "__main__":
    generate_shap_explanations()
