
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from .training import create_models, FEATURES, TARGET


BACKEND = Path(__file__).resolve().parents[3]

DATA_DIR = BACKEND / "data/c2/yield/processed"
MODEL_DIR = BACKEND / "models/c2/yield"
RESULT_DIR = BACKEND / "experiments/c2/yield"


def evaluate_final_test():
    print("Loading development and final test datasets...")

    development = pd.read_csv(
        DATA_DIR / "peerj_development.csv"
    )

    test = pd.read_csv(
        DATA_DIR / "peerj_test.csv"
    )

    # Verify that test genotypes were never
    # included in development data.
    dev_groups = set(development["genotype_id"])
    test_groups = set(test["genotype_id"])

    if not dev_groups.isdisjoint(test_groups):
        raise ValueError("Genotype leakage detected!")

    if not test["cv_fold"].eq(-1).all():
        raise ValueError("Unexpected test fold assignments")

    print("Development rows:", len(development))
    print("Test rows:", len(test))
    print("Test genotypes:", len(test_groups))
    print("Genotype overlap: NONE")

    X_train = development[FEATURES]
    y_train = development[TARGET]

    X_test = test[FEATURES]
    y_test = test[TARGET]

    # Freeze model choices before evaluating test.
    tuned_path = (
        MODEL_DIR / "xgboost_tuned_development.joblib"
    )

    if not tuned_path.exists():
        raise FileNotFoundError(
            "Tuned XGBoost model not found"
        )

    # Load only our own trusted model file.
    tuned_xgboost = joblib.load(tuned_path)

    models = {
        "Tuned XGBoost": tuned_xgboost,
        "Random Forest": create_models()["Random Forest"],
        "SVR": create_models()["SVR"],
        "Training Mean": create_models()["Training Mean"],
    }

    results = []
    prediction_rows = []

    print("\n===== FINAL HELD-OUT TEST =====")

    for name, model in models.items():

        # XGBoost was fitted already by RandomizedSearchCV.
        # Baselines use their previously fixed settings.
        if name != "Tuned XGBoost":
            model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        mae = mean_absolute_error(
            y_test, predictions
        )

        rmse = np.sqrt(
            mean_squared_error(y_test, predictions)
        )

        r2 = r2_score(
            y_test, predictions
        )

        results.append({
            "model": name,
            "MAE_g_per_plant": float(mae),
            "RMSE_g_per_plant": float(rmse),
            "R2": float(r2),
        })

        for genotype, actual, predicted in zip(
            test["genotype_id"],
            y_test,
            predictions,
        ):
            prediction_rows.append({
                "model": name,
                "genotype_id": genotype,
                "actual_yield_g": float(actual),
                "predicted_yield_g": float(predicted),
            })

        print(
            f"{name}: "
            f"MAE={mae:.3f}, "
            f"RMSE={rmse:.3f}, "
            f"R2={r2:.3f}"
        )

    RESULT_DIR.mkdir(
        parents=True, exist_ok=True
    )

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        RESULT_DIR / "yield_final_test_metrics.csv",
        index=False,
    )

    pd.DataFrame(prediction_rows).to_csv(
        RESULT_DIR / "yield_final_test_predictions.csv",
        index=False,
    )

    print("\nFinal test evaluation completed.")
    print("Results saved to:", RESULT_DIR)


if __name__ == "__main__":
    evaluate_final_test()
