
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from xgboost import XGBRegressor


# Project paths
BACKEND = Path(__file__).resolve().parents[3]

DATA_FILE = (
    BACKEND / "data/c2/yield/processed"
    / "peerj_development.csv"
)

RESULT_DIR = BACKEND / "experiments/c2/yield"
MODEL_DIR = BACKEND / "models/c2/yield"

RANDOM_STATE = 42

# Only use selected plant traits
FEATURES = [
    "plant_height_cm",
    "main_branches",
    "leaf_length_cm",
    "leaf_breadth_cm",
    "days_to_50pct_flowering",
]

TARGET = "fruit_yield_g_per_plant"


def create_models():
    """
    Create fresh ML pipelines.

    Imputation/scaling are fitted separately
    inside each training fold.
    """
    return {
        "XGBoost": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", XGBRegressor(
                n_estimators=200,
                max_depth=3,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                objective="reg:squarederror",
                random_state=RANDOM_STATE,
                n_jobs=2,
            )),
        ]),

        "Random Forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(
                n_estimators=200,
                max_depth=6,
                min_samples_leaf=2,
                random_state=RANDOM_STATE,
                n_jobs=2,
            )),
        ]),

        "SVR": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", SVR(
                kernel="rbf",
                C=10.0,
                epsilon=0.1,
            )),
        ]),

        "Training Mean": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", DummyRegressor(strategy="mean")),
        ]),
    }


def calculate_metrics(actual, predicted):
    return {
        "MAE": float(
            mean_absolute_error(actual, predicted)
        ),
        "RMSE": float(
            np.sqrt(mean_squared_error(actual, predicted))
        ),
        "R2": float(
            r2_score(actual, predicted)
        ),
    }


def train_with_grouped_cv():
    print("Loading development dataset...")

    df = pd.read_csv(DATA_FILE)

    required = FEATURES + [
        TARGET,
        "genotype_id",
        "cv_fold",
    ]

    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if df[required].isna().any().any():
        # Missing predictors can be handled by the
        # fold-specific imputer, but IDs, target,
        # and CV assignments must be complete.
        critical = ["genotype_id", TARGET, "cv_fold"]
        if df[critical].isna().any().any():
            raise ValueError("Missing critical values")

    if df["cv_fold"].nunique() != 5:
        raise ValueError("Expected exactly five CV folds")

    if set(df["cv_fold"].unique()) != {1, 2, 3, 4, 5}:
        raise ValueError("Invalid CV fold assignments")

    if df.groupby("genotype_id")["cv_fold"].nunique().max() != 1:
        raise ValueError("Genotype leakage across folds")

    X = df[FEATURES].apply(
        pd.to_numeric, errors="coerce"
    )

    y = pd.to_numeric(df[TARGET], errors="raise")

    if not np.isfinite(y).all():
        raise ValueError("Invalid yield targets")

    fold_results = []
    predictions = []

    print("Development records:", len(df))
    print("Unique genotypes:", df["genotype_id"].nunique())

    print("\nStarting grouped 5-fold cross-validation...")

    for fold in range(1, 6):
        train_mask = df["cv_fold"] != fold
        val_mask = df["cv_fold"] == fold

        train_groups = set(
            df.loc[train_mask, "genotype_id"]
        )
        val_groups = set(
            df.loc[val_mask, "genotype_id"]
        )

        if not train_groups.isdisjoint(val_groups):
            raise ValueError("Genotype leakage detected")

        X_train = X.loc[train_mask]
        X_val = X.loc[val_mask]

        y_train = y.loc[train_mask]
        y_val = y.loc[val_mask]

        print(f"\nFold {fold}")

        for name, model in create_models().items():
            model.fit(X_train, y_train)

            pred = model.predict(X_val)

            scores = calculate_metrics(y_val, pred)

            fold_results.append({
                "model": name,
                "fold": fold,
                "train_rows": len(X_train),
                "validation_rows": len(X_val),
                **scores,
            })

            for idx, prediction in zip(
                X_val.index, pred
            ):
                predictions.append({
                    "model": name,
                    "fold": fold,
                    "genotype_id": df.loc[
                        idx, "genotype_id"
                    ],
                    "actual_yield_g": float(y.loc[idx]),
                    "predicted_yield_g": float(prediction),
                })

            print(
                f"  {name}: "
                f"MAE={scores['MAE']:.2f}, "
                f"RMSE={scores['RMSE']:.2f}, "
                f"R2={scores['R2']:.3f}"
            )

    results = pd.DataFrame(fold_results)

    # Fold-level mean and standard deviation
    summary = (
        results.groupby("model")[
            ["MAE", "RMSE", "R2"]
        ]
        .agg(["mean", "std"])
    )

    summary.columns = [
        f"{metric}_{stat}"
        for metric, stat in summary.columns
    ]

    summary = summary.sort_values("MAE_mean")

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    results.to_csv(
        RESULT_DIR / "yield_cv_fold_metrics.csv",
        index=False,
    )

    summary.to_csv(
        RESULT_DIR / "yield_cv_summary.csv"
    )

    pd.DataFrame(predictions).to_csv(
        RESULT_DIR / "yield_cv_predictions.csv",
        index=False,
    )

    # Refit the planned primary model using
    # all development data, never the held-out test.
    primary_model = create_models()["XGBoost"]
    primary_model.fit(X, y)

    joblib.dump(
        primary_model,
        MODEL_DIR / "xgboost_yield_development.joblib",
    )

    metadata = {
        "model": "XGBoost",
        "experiment": "PeerJ genotype-year yield regression",
        "features": FEATURES,
        "target": TARGET,
        "target_unit": "g/plant",
        "fresh_or_dry": "not explicitly verified",
        "cv_method": "5-fold genotype-grouped",
        "development_rows": len(df),
        "test_evaluated": False,
        "random_state": RANDOM_STATE,
    }

    (
        MODEL_DIR / "yield_model_metadata.json"
    ).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\n===== CV SUMMARY =====")
    print(summary.round(3).to_string())

    print("\nPrimary XGBoost model saved.")
    print("Final held-out test NOT evaluated.")
    print("Step 7 completed.")


if __name__ == "__main__":
    train_with_grouped_cv()
