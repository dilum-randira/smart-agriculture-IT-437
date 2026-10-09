"""Educational yield regression baseline using synthetic examples only.

This is NOT a Nai Miris yield model and produces no field-validation evidence.
"""

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

FEATURES = ["soil_moisture", "temperature", "humidity", "crop_age"]


def make_practice_data(n=300, seed=42):
    """Create independent synthetic rows for understanding supervised regression."""
    rng = np.random.default_rng(seed)
    data = pd.DataFrame({
        "soil_moisture": rng.uniform(15, 55, n),
        "temperature": rng.uniform(24, 36, n),
        "humidity": rng.uniform(45, 90, n),
        "crop_age": rng.integers(30, 105, n),
    })
    # Made-up training relationship, NOT a scientifically calibrated crop equation.
    data["yield_kg"] = (
        0.7
        + 0.025 * data["crop_age"]
        + 0.05 * data["soil_moisture"]
        - 0.1 * abs(data["temperature"] - 29)
        + rng.normal(0, 0.35, n)
    ).clip(lower=0.1)
    return data


def evaluate_model(model, x_test, y_test):
    predicted = model.predict(x_test)
    return {
        "MAE": float(mean_absolute_error(y_test, predicted)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, predicted))),
        "R2": float(r2_score(y_test, predicted)),
    }


def run_experiment():
    data = make_practice_data()
    x_train, x_test, y_train, y_test = train_test_split(
        data[FEATURES], data["yield_kg"], test_size=0.2, random_state=42
    )

    baseline = DummyRegressor(strategy="mean")
    baseline.fit(x_train, y_train)

    forest = RandomForestRegressor(n_estimators=100, random_state=42)
    forest.fit(x_train, y_train)

    results = {
        "Training Mean": evaluate_model(baseline, x_test, y_test),
        "Random Forest": evaluate_model(forest, x_test, y_test),
    }

    # The hypothetical sample uses exactly the same feature names and units.
    new_sample = pd.DataFrame([{
        "soil_moisture": 35,
        "temperature": 29,
        "humidity": 75,
        "crop_age": 70,
    }])
    sample_prediction = float(forest.predict(new_sample[FEATURES])[0])
    return results, sample_prediction


if __name__ == "__main__":
    scores, hypothetical_yield = run_experiment()
    print("PRACTICE ONLY: synthetic, non-field data")
    for name, metrics in scores.items():
        print(f"\n{name}")
        for metric, value in metrics.items():
            print(f"  {metric}: {value:.4f}")
    print(f"\nHypothetical prediction: {hypothetical_yield:.2f} kg")
