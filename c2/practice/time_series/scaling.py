"""Scale sequence inputs using TRAINING inputs only, preventing test leakage."""

import numpy as np
from sklearn.preprocessing import StandardScaler


def fit_train_only_scaler(splits):
    scaler = StandardScaler()
    scaler.fit(splits["train"]["X"].reshape(-1, 1))
    return scaler


def transform_splits(splits, scaler):
    result = {}
    for group in ("train", "validation", "test"):
        sample = splits[group]
        result[group] = {
            "X": scaler.transform(sample["X"].reshape(-1, 1)).reshape(sample["X"].shape)[..., None],
            "y": scaler.transform(sample["y"].reshape(-1, 1)).reshape(sample["y"].shape),
            "origins": sample["origins"].copy(),
        }
    result["boundaries"] = splits["boundaries"].copy()
    return result


def inverse_forecast(scaled_prediction, scaler):
    values = np.asarray(scaled_prediction)
    if values.ndim != 2:
        raise ValueError("expected [number of forecasts, horizon] array")
    return scaler.inverse_transform(values.reshape(-1, 1)).reshape(values.shape)
