"""Causal preprocessing and complete-label windows; no estimator fitting."""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

LABEL = "Synthetic Data — Prototype Evaluation Only"
TARGETS = ("soil_moisture_avg_index", "air_temperature_c", "relative_humidity_pct")
UNITS = ("index (not volumetric water content)", "°C", "% RH")
EXCLUDED = ("forecast_rain_mm_next_24h", "forecast_air_temp_max_c_next_24h")
NUMERIC = ("soil_moisture_1_index", "soil_moisture_2_index", *TARGETS,
           "soil_temperature_c", "light_lux", "rainfall_mm_24h", *EXCLUDED,
           "soil_moisture_change_1h_index", "air_temperature_avg_24h_c", "vpd_kpa", "quality_score")
BOOLS = ("rain_detected", "is_anomaly", "is_imputed")
SCHEMA = {"timestamp", "node_id", "zone_id", "imputed_fields", "record_status", "data_origin", *NUMERIC, *BOOLS}
FUTURE_FEATURE_CONTRACT = {"growth_stage": "unavailable; needs observed label and availability timestamp",
                           "planting_date": "unavailable; never inferred", "crop_age": "unavailable; never fabricated"}


@dataclass(frozen=True)
class Config:
    lookback: int = 336
    horizon: int = 168
    train_fraction: float = .70
    validation_fraction: float = .15
    stride: int = 1

    def __post_init__(self):
        if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in (self.lookback, self.horizon, self.stride)):
            raise ValueError("Window lengths and stride must be positive integers")
        if not (0 < self.train_fraction < 1 and 0 < self.validation_fraction < 1 and self.train_fraction + self.validation_fraction < 1):
            raise ValueError("Invalid split fractions")


def validate(frame):
    """Reject structural corruption; retain quality-marked rows for causal masking."""
    d = frame.copy()
    if set(d.columns) != SCHEMA or d.columns.duplicated().any():
        raise ValueError(f"Schema mismatch: missing={SCHEMA-set(d.columns)}, extra={set(d.columns)-SCHEMA}")
    if d.empty:
        raise ValueError("Empty dataset")
    for c in SCHEMA - {"imputed_fields"}:
        if d[c].isna().any():
            raise ValueError(f"Missing required values: {c}")
    for c in NUMERIC:
        d[c] = pd.to_numeric(d[c], errors="raise")
        if not np.isfinite(d[c]).all():
            raise ValueError(f"Non-finite numeric values: {c}")
    for c in BOOLS:
        if not d[c].map(lambda v: isinstance(v, (bool, np.bool_))).all():
            raise ValueError(f"Invalid boolean: {c}")
    for c in ("node_id", "zone_id"):
        if not d[c].map(lambda v: isinstance(v, str) and bool(v.strip())).all():
            raise ValueError(f"Invalid identifier: {c}")
    if set(d.record_status) - {"OK", "WARN", "INVALID"} or set(d.data_origin) != {"synthetic"}:
        raise ValueError("Unexpected status or non-synthetic origin")
    if ((d.quality_score < 0) | (d.quality_score > 1)).any():
        raise ValueError("Quality score outside [0,1]")
    if ((d.relative_humidity_pct < 0) | (d.relative_humidity_pct > 100)).any():
        raise ValueError("Relative humidity outside [0,100]")
    for c in ("soil_moisture_1_index", "soil_moisture_2_index", "soil_moisture_avg_index", "light_lux", "rainfall_mm_24h", "forecast_rain_mm_next_24h", "vpd_kpa"):
        if (d[c] < 0).any():
            raise ValueError(f"Negative value: {c}")
    if not d.imputed_fields.dropna().map(lambda v: isinstance(v, str)).all():
        raise ValueError("Imputed fields must be strings or empty")
    d.imputed_fields = d.imputed_fields.fillna("").str.strip()
    if not (d.imputed_fields.ne("") == d.is_imputed).all():
        raise ValueError("Imputed flag/field mismatch")
    for names in d.imputed_fields:
        if names and set(names.split(",")) - set(NUMERIC):
            raise ValueError("Unknown imputed field")
    if ((d.is_imputed | d.is_anomaly) & d.record_status.eq("OK")).any():
        raise ValueError("Flagged record incorrectly marked OK")
    # Require explicit timezone before UTC parsing; never silently localize naive values.
    timestamps = [pd.Timestamp(v) for v in d.timestamp]
    if any(t.tzinfo is None or pd.isna(t) for t in timestamps):
        raise ValueError("Timezone-aware timestamps required")
    d.timestamp = pd.to_datetime(d.timestamp, utc=True).dt.tz_convert("Asia/Colombo")
    if (d.timestamp.dt.minute.ne(0) | d.timestamp.dt.second.ne(0) | d.timestamp.dt.microsecond.ne(0) | d.timestamp.dt.nanosecond.ne(0)).any():
        raise ValueError("Timestamps must align to hourly boundaries")
    if d.duplicated(["node_id", "timestamp"]).any():
        raise ValueError("Duplicate node/timestamp")
    d = d.sort_values(["node_id", "timestamp"]).reset_index(drop=True)
    for _, g in d.groupby("node_id"):
        if g.zone_id.nunique() != 1 or not g.timestamp.diff().iloc[1:].eq(pd.Timedelta(hours=1)).all():
            raise ValueError("Node zone changes or hourly gaps")
    return d


def load(path):
    return validate(pd.read_csv(path))


def quality_valid(d):
    # Supplied imputation has no causal provenance. Do not treat it as ground truth.
    return ~(d.record_status.eq("INVALID") | d.is_anomaly | d.is_imputed)


def partitions(d, config):
    """Common calendar cutoffs, computed BEFORE quality filtering/window generation."""
    times = pd.DatetimeIndex(d.timestamp.unique()).sort_values()
    a = int(len(times) * config.train_fraction)
    b = int(len(times) * (config.train_fraction + config.validation_fraction))
    if not (0 < a < b < len(times)):
        raise ValueError("Too few timestamps for splits")
    return {"train": (times[0], times[a-1]), "validation": (times[a], times[b-1]), "test": (times[b], times[-1])}


def windows(part, config):
    """Original complete-case interface, retained for reproducibility."""
    x, y, _, origins, candidates = _window_arrays(part, config, config.horizon)
    return x, y, origins, candidates


def masked_windows(part, config, minimum_target_fraction=.95):
    """Return X, raw y, boolean target mask, origins, candidate count.

    Require ceil(.95*horizon) usable hours PER target by default (160/168).
    Masked-out y values remain source values, never filled ground truth.
    The mask is mandatory for any downstream loss/evaluation.
    """
    if not np.isfinite(minimum_target_fraction) or not 0 < minimum_target_fraction <= 1:
        raise ValueError("Minimum target fraction must be in (0,1]")
    minimum = max(1, int(np.ceil(minimum_target_fraction * config.horizon)))
    return _window_arrays(part, config, minimum)


def _window_arrays(part, config, minimum_valid_hours):
    """One node/partition; target quality captured BEFORE history filling."""
    if part.node_id.nunique() != 1:
        raise ValueError("Window generation requires exactly one node")
    part = part.sort_values("timestamp").reset_index(drop=True)
    if not part.timestamp.diff().iloc[1:].eq(pd.Timedelta(hours=1)).all():
        raise ValueError("Non-hourly window input")
    valid = quality_valid(part).to_numpy()
    raw = part.loc[:, TARGETS].to_numpy(dtype=np.float64)
    target_valid = np.repeat(valid[:, None], 3, axis=1)
    history = pd.DataFrame(np.where(valid[:, None], raw, np.nan)).ffill().to_numpy()
    timestamps = pd.DatetimeIndex(part.timestamp)
    xs, ys, masks, origins = [], [], [], []
    candidates = max(0, (len(part)-config.lookback-config.horizon)//config.stride+1)
    for t in range(config.lookback, len(part)-config.horizon+1, config.stride):
        x = history[t-config.lookback:t]
        mask = target_valid[t:t+config.horizon]
        if not np.isfinite(x).all() or not (mask.sum(axis=0) >= minimum_valid_hours).all():
            continue
        assert timestamps[t]-timestamps[t-1] == pd.Timedelta(hours=1)
        assert timestamps[t-config.lookback] >= timestamps[0]
        assert timestamps[t+config.horizon-1] <= timestamps[-1]
        xs.append(x); ys.append(raw[t:t+config.horizon]); masks.append(mask); origins.append(timestamps[t-1])
    x = np.asarray(xs, dtype=np.float64).reshape(-1, config.lookback, 3)
    y = np.asarray(ys, dtype=np.float64).reshape(-1, config.horizon, 3)
    mask = np.asarray(masks, dtype=bool).reshape(-1, config.horizon, 3)
    assert x.shape == (len(origins), config.lookback, 3)
    assert y.shape == (len(origins), config.horizon, 3)
    assert mask.shape == y.shape
    assert (mask.sum(axis=1) >= minimum_valid_hours).all()
    assert np.isfinite(x).all() and np.isfinite(y).all()
    return x, y, mask, origins, candidates


def persistence(x, horizon=168):
    if x.ndim != 3 or x.shape[2] != 3 or x.shape[1] == 0 or horizon <= 0 or not np.isfinite(x).all():
        raise ValueError("Invalid persistence input")
    return np.repeat(x[:, -1:, :], horizon, axis=1)


def scores(actual, predicted):
    if actual.shape != predicted.shape or actual.ndim != 3 or actual.shape[2] != 3:
        raise ValueError("Prediction/target shape mismatch")
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("Non-finite evaluation")
    n, horizon, _ = actual.shape
    rows, leads = [], []
    for j, target in enumerate(TARGETS):
        for h in (24, 72, 168):
            if h > horizon:
                continue
            error = predicted[:, :h, j] - actual[:, :h, j]
            rows.append(dict(target=target, unit=UNITS[j], window_hours=h, samples=n,
                             forecast_values=n*h, MAE=float(np.abs(error).mean()) if n else None,
                             RMSE=float(np.sqrt(np.square(error).mean())) if n else None, evaluation_label=LABEL))
        for h in range(horizon):
            error = predicted[:, h, j] - actual[:, h, j]
            leads.append(dict(target=target, unit=UNITS[j], lead_hour=h+1, samples=n,
                              MAE=float(np.abs(error).mean()) if n else None,
                              RMSE=float(np.sqrt(np.square(error).mean())) if n else None, evaluation_label=LABEL))
    return rows, leads


def _eligible_errors(actual, predicted, mask):
    actual, predicted, mask = np.asarray(actual), np.asarray(predicted), np.asarray(mask)
    if actual.shape != predicted.shape or actual.shape != mask.shape:
        raise ValueError("Target, prediction and mask shapes must match")
    if mask.dtype != np.bool_ and not np.isin(mask, [0, 1]).all():
        raise ValueError("Target mask must contain only boolean/0/1 values")
    mask = mask.astype(bool)
    # Select before subtraction: NaN*0 is NaN, not an excluded observation.
    a, p = actual[mask], predicted[mask]
    if not np.isfinite(a).all() or not np.isfinite(p).all():
        raise ValueError("Non-finite eligible target/prediction")
    return p-a


def masked_regression_loss(actual, predicted, target_valid_mask, kind="mse"):
    """NumPy reference loss contract; denominator is eligible cells, never N*H.

    Returns None if no eligible observations. Phase 2 must implement the same
    selection/normalization with its differentiable backend; no models here.
    """
    if kind not in {"mse", "mae"}:
        raise ValueError("Loss kind must be mse or mae")
    error = _eligible_errors(actual, predicted, target_valid_mask)
    if not error.size:
        return None
    return float(np.square(error).mean() if kind == "mse" else np.abs(error).mean())


def masked_scores(actual, predicted, target_valid_mask):
    """Per-target cumulative and lead metrics using eligible observations only."""
    if actual.ndim != 3 or actual.shape[2] != 3 or actual.shape != predicted.shape or actual.shape != target_valid_mask.shape:
        raise ValueError("Expected matching [N,horizon,3] target/prediction/mask")
    _eligible_errors(actual, predicted, target_valid_mask)
    n, horizon, _ = actual.shape
    mask = target_valid_mask.astype(bool)
    rows, leads = [], []

    def statistics(a, p, m):
        error = _eligible_errors(a, p, m)
        count = int(m.sum())
        return dict(samples=n, contributing_samples=int(m.reshape(n, -1).any(axis=1).sum()) if n else 0,
                    valid_observations=count, possible_observations=int(m.size),
                    masked_observations=int(m.size-count), coverage_fraction=count/m.size if m.size else None,
                    MAE=float(np.abs(error).mean()) if count else None,
                    RMSE=float(np.sqrt(np.square(error).mean())) if count else None,
                    evaluation_label=LABEL)

    for j, target in enumerate(TARGETS):
        for h in (24, 72, 168):
            if h <= horizon:
                rows.append(dict(target=target, unit=UNITS[j], window_hours=h,
                                 **statistics(actual[:, :h, j], predicted[:, :h, j], mask[:, :h, j])))
        for h in range(horizon):
            leads.append(dict(target=target, unit=UNITS[j], lead_hour=h+1,
                              **statistics(actual[:, h:h+1, j], predicted[:, h:h+1, j], mask[:, h:h+1, j])))
    return rows, leads
