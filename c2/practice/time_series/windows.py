"""Leakage-aware sequence window creation for one observed target variable.

Each sample uses only previous observations as input. Target periods belong
entirely to train, validation, or test; a target never straddles a boundary.
Validation/test inputs MAY include history before their split boundary.
"""

import numpy as np


def chronological_windows(series, lookback=48, horizon=24, stride=6,
                          train_fraction=0.70, validation_fraction=0.15):
    values = np.asarray(series, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("series must be a one-dimensional array of finite numbers")
    if lookback < 1 or horizon < 1 or stride < 1:
        raise ValueError("lookback, horizon and stride must be positive")
    if not (0 < train_fraction < 1 and 0 < validation_fraction < 1
            and train_fraction + validation_fraction < 1):
        raise ValueError("invalid train/validation fractions")

    n = len(values)
    train_end = int(n * train_fraction)
    val_end = int(n * (train_fraction + validation_fraction))
    split_rows = {key: [] for key in ("train", "validation", "test")}

    for origin in range(lookback, n - horizon + 1, stride):
        target_end = origin + horizon
        if target_end <= train_end:
            group = "train"
        elif origin >= train_end and target_end <= val_end:
            group = "validation"
        elif origin >= val_end and target_end <= n:
            group = "test"
        else:
            continue  # drop windows whose target crosses a split boundary
        split_rows[group].append((values[origin - lookback:origin],
                                  values[origin:target_end], origin))

    result = {}
    for key, rows in split_rows.items():
        if not rows:
            raise ValueError(f"No eligible {key} windows; use more history or shorter windows")
        result[key] = {
            "X": np.stack([row[0] for row in rows]),
            "y": np.stack([row[1] for row in rows]),
            "origins": np.array([row[2] for row in rows], dtype=int),
        }
    result["boundaries"] = {"train_end": train_end, "validation_end": val_end, "length": n}
    return result
