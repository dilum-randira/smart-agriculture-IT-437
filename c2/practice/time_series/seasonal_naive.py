"""Daily seasonal-naive reference for hourly data (no machine learning).

The input is past-observed hourly history; repeat the last full 24h cycle.
Daily patterns are prominent in the synthetic educational dataset. This is a
useful additional *simple* reference, not a C2 learned baseline.
"""

import numpy as np


def seasonal_naive_forecast(x, horizon, season_length=24):
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[0] == 0 or not np.isfinite(x).all():
        raise ValueError("x must be a nonempty finite 2-D observation-window array")
    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be positive integer")
    if not isinstance(season_length, int) or season_length < 1 or x.shape[1] < season_length:
        raise ValueError("season_length must fit within the observed lookback window")
    latest_cycle = x[:, -season_length:]
    return latest_cycle[:, np.arange(horizon) % season_length]
