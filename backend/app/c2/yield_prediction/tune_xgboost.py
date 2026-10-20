
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.model_selection import (
    PredefinedSplit,
    RandomizedSearchCV,
)
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor


BACKEND = Path(__file__).resolve().parents[3]

DATA_FILE = (
    BACKEND / "data/c2/yield/processed"
    / "peerj_development.csv"
)

RESULT_DIR = BACKEND / "experiments/c2/yield"
MODEL_DIR = BACKEND / "models/c2/yield"

FEATURES = [
    "plant_height_cm",
    "main_branches",
    "leaf_length_cm",
    "leaf_breadth_cm",
    "days_to_50pct_flowering",
]

TARGET = "fruit_yield_g_per_plant"


def tune_xgboost():
    print("Loading development data...")
    df = pd.read_csv(DATA_FILE)

    X = df[FEATURES].apply(
        pd.to_numeric, errors="coerce"
    )
    y = pd.to_numeric(
        df[TARGET], errors="raise"
    )

    if not np.isfinite(y).all():
        raise ValueError("Invalid target values")

    if set(df["cv_fold"].unique()) != {1, 2, 3, 4, 5}:
        raise ValueError("Unexpected CV folds")

    if df.groupby("genotype_id")["cv_fold"].nunique().max() != 1:
        raise ValueError("Genotype leakage detected")

    # Reuse the exact same grouped folds
    cv = PredefinedSplit(
        test_fold=df["cv_fold"].to_numpy() - 1
    )

    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", XGBRegressor(
            objective="reg:squarederror",
            random_state=42,
            n_jobs=2,
        )),
    ])

    parameters = {
        "model__n_estimators": [100, 200, 350],
        "model__max_depth": [1, 2, 3],
        "model__learning_rate": [0.02, 0.05, 0.1],
        "model__min_child_weight": [1, 3, 5],
        "model__subsample": [0.8, 1.0],
        "model__colsample_bytree": [0.8, 1.0],
        "model__reg_lambda": [1, 5, 10],
    }

    search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=parameters,
        n_iter=12,
        scoring="neg_mean_absolute_error",
        cv=cv,
        refit=True,
        random_state=42,
        n_jobs=1,
        verbose=1,
        error_score="raise",
    )

    print("Starting grouped CV hyperparameter search...")
    search.fit(X, y)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    results = pd.DataFrame(search.cv_results_)
    results.to_csv(
        RESULT_DIR / "xgboost_tuning_results.csv",
        index=False,
    )

    joblib.dump(
        search.best_estimator_,
        MODEL_DIR / "xgboost_tuned_development.joblib",
    )

    metadata = {
        "model": "XGBoost",
        "dataset": "PeerJ genotype-year aggregates",
        "target": TARGET,
        "features": FEATURES,
        "selection_metric": "CV MAE",
        "best_cv_mae": float(-search.best_score_),
        "best_parameters": search.best_params_,
        "cv_method": "Predefined genotype-grouped 5-fold",
        "test_evaluated": False,
    }

    (
        MODEL_DIR / "xgboost_tuning_metadata.json"
    ).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\n===== TUNING RESULTS =====")
    print("Best CV MAE:", round(-search.best_score_, 3))
    print("Best parameters:")

    for key, value in search.best_params_.items():
        print(f"  {key}: {value}")

    print("\nTuned development model saved.")
    print("Final test data was NOT used.")


if __name__ == "__main__":
    tune_xgboost()
