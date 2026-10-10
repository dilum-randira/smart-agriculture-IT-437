"""No-training persistence reference: repeat the latest known observation."""

import numpy as np


def persistence_forecast(x, horizon):
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] < 1 or horizon < 1:
        raise ValueError("x must be a nonempty 2-D window array and horizon >= 1")
    return np.repeat(x[:, -1:], horizon, axis=1)


def horizon_scores(y_true, y_pred, horizons=(6, 12, 24)):
    actual, predicted = np.asarray(y_true), np.asarray(y_pred)
    if actual.shape != predicted.shape or actual.ndim != 2 or actual.shape[0] == 0:
        raise ValueError("actual and predictions need identical nonempty 2-D shapes")
    result = {}
    for horizon in horizons:
        if not (1 <= horizon <= actual.shape[1]):
            raise ValueError("requested horizon exceeds available target steps")
        error = actual[:, :horizon] - predicted[:, :horizon]
        result[horizon] = {
            "MAE": float(np.abs(error).mean()),
            "RMSE": float(np.sqrt(np.square(error).mean())),
        }
    return result
