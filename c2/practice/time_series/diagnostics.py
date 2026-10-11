"""Lead-time and cumulative forecast diagnostics for teaching.

Metrics are calculated on test targets only when the caller explicitly passes
held-out targets. Rolling windows may overlap: values are NOT independent
field replications and shouldn't be used as independent uncertainty samples.
"""

import numpy as np


def validate_forecasts(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    if actual.ndim != 2 or actual.shape != predicted.shape or not actual.size:
        raise ValueError("actual and predicted must be nonempty matching 2-D arrays")
    if not (np.isfinite(actual).all() and np.isfinite(predicted).all()):
        raise ValueError("forecast arrays must contain only finite numbers")
    return actual, predicted


def lead_time_metrics(actual, predicted):
    """One MAE/RMSE pair per forecast lead, across test forecast origins."""
    actual, predicted = validate_forecasts(actual, predicted)
    error = actual - predicted
    return {
        "lead_hour": np.arange(1, actual.shape[1] + 1, dtype=int),
        "mae": np.abs(error).mean(axis=0),
        "rmse": np.sqrt(np.square(error).mean(axis=0)),
    }


def cumulative_metrics(actual, predicted, horizons=(6, 12, 24)):
    """For horizon H, summarize all steps 1..H (not just step H)."""
    actual, predicted = validate_forecasts(actual, predicted)
    scores = {}
    for horizon in horizons:
        if not isinstance(horizon, int) or not 1 <= horizon <= actual.shape[1]:
            raise ValueError("each horizon must be a valid integer forecast length")
        error = actual[:, :horizon] - predicted[:, :horizon]
        scores[horizon] = {
            "MAE": float(np.abs(error).mean()),
            "RMSE": float(np.sqrt(np.square(error).mean())),
            "forecast_origins": int(actual.shape[0]),
        }
    return scores
