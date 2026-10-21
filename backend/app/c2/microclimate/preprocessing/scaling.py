"""Train-only, unique-observation standardization; no models or new imputation."""
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from .pipeline import TARGETS, quality_valid


def boolean_mask(mask, shape):
    mask = np.asarray(mask)
    if mask.shape != shape or (mask.dtype != np.bool_ and not np.isin(mask, [0, 1]).all()):
        raise ValueError("Expected matching boolean/0/1 observation mask")
    return mask.astype(bool)


@dataclass(frozen=True)
class Standardizer:
    features: tuple
    mean: tuple
    variance: tuple
    std: tuple
    scale: tuple
    counts: tuple

    def _values(self, values, feature_names):
        if tuple(feature_names) != self.features:
            raise ValueError("Feature order differs from fitted scaler contract")
        values = np.asarray(values, dtype=np.float64)
        if values.ndim < 2 or values.shape[-1] != len(self.features):
            raise ValueError("Expected [...,features] array")
        return values

    def transform(self, values, feature_names):
        values = self._values(values, feature_names)
        if not np.isfinite(values).all():
            raise ValueError("Non-finite input")
        result = ((values-np.asarray(self.mean))/np.asarray(self.scale)).astype(np.float32)
        if not np.isfinite(result).all():
            raise ValueError("Scaled input cannot be represented as finite float32")
        return result

    def transform_targets(self, values, mask, feature_names):
        """Exclude before arithmetic; mask=False => finite standardized zero placeholder."""
        values = self._values(values, feature_names)
        mask = boolean_mask(mask, values.shape)
        result = np.zeros(values.shape, dtype=np.float32)
        for j in range(len(self.features)):
            selected = values[..., j][mask[..., j]]
            if not np.isfinite(selected).all():
                raise ValueError("Non-finite eligible target")
            result[..., j][mask[..., j]] = (selected-self.mean[j])/self.scale[j]
        if not np.isfinite(result).all():
            raise ValueError("Scaled target cannot be represented as finite float32")
        return result

    def inverse_transform(self, values, feature_names):
        """Predictions or inputs -> float64 original units, with no clipping."""
        values = self._values(values, feature_names)
        if not np.isfinite(values).all():
            raise ValueError("Non-finite scaled values")
        result = values*np.asarray(self.scale)+np.asarray(self.mean)
        if not np.isfinite(result).all():
            raise ValueError("Non-finite inverse transform")
        return result

    def inverse_targets(self, values, mask, feature_names):
        """Actual targets only: masked placeholders remain unavailable, never ground truth."""
        values = self._values(values, feature_names)
        mask = boolean_mask(mask, values.shape)
        result = np.full(values.shape, np.nan, dtype=np.float64)
        for j in range(len(self.features)):
            selected = values[..., j][mask[..., j]]
            if not np.isfinite(selected).all():
                raise ValueError("Non-finite eligible scaled target")
            result[..., j][mask[..., j]] = selected*self.scale[j]+self.mean[j]
        return result

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, saved):
        # Keep serialized JSON portable; no pickle/joblib execution required.
        result = cls(**{key: tuple(saved[key]) for key in
                        ("features", "mean", "variance", "std", "scale", "counts")})
        n = len(result.features)
        if n != 3 or len(set(result.features)) != n or any(len(getattr(result, k)) != n for k in
                                                          ("mean", "variance", "std", "scale", "counts")):
            raise ValueError("Malformed scaler metadata")
        if not np.isfinite([result.mean, result.variance, result.std, result.scale]).all():
            raise ValueError("Non-finite scaler metadata")
        if any(v <= 0 for v in result.scale) or any(v < 0 for v in result.variance+result.std) or any(n <= 0 for n in result.counts):
            raise ValueError("Invalid scale/variance/count metadata")
        return result


def fit_standardizer(values, eligible, feature_names=TARGETS):
    """Fit population mean/variance on already deduplicated genuine observations.

    StandardScaler convention: ddof=0; numerical constant-feature scale=1.
    Caller must supply a unique training node/timestamp table, not flattened windows.
    """
    values = np.asarray(values, dtype=np.float64)
    if tuple(feature_names) != TARGETS or values.ndim != 2 or values.shape[1] != 3:
        raise ValueError("Expected unique observation table in fixed target/feature order")
    mask = boolean_mask(eligible, values.shape)
    means, variances, stds, scales, counts = [], [], [], [], []
    eps = np.finfo(np.float64).eps
    for j in range(3):
        selected = values[:, j][mask[:, j]]
        if not len(selected) or not np.isfinite(selected).all():
            raise ValueError("No finite eligible training observations for feature")
        mean = float(selected.mean())
        variance = float(selected.var(ddof=0))
        std = float(np.sqrt(variance))
        # Same floating-point constant-feature safeguard as StandardScaler.
        constant_bound = len(selected)*eps*variance+(len(selected)*mean*eps)**2
        scale = 1.0 if variance <= constant_bound else std
        means.append(mean); variances.append(variance); stds.append(std)
        scales.append(scale); counts.append(len(selected))
    return Standardizer(tuple(feature_names), tuple(means), tuple(variances), tuple(stds), tuple(scales), tuple(counts))


def training_fit_observations(data, train_start, train_end, training_origins, config):
    """Unique genuine source rows used by retained TRAIN histories/targets.

    Both nodes share scalers. The input and target pools differ by temporal role.
    Repeated origins and overlapping windows cannot increase a row's weight.
    Validation/test rows are removed before numeric selection or statistics.
    """
    train = data[data.timestamp.between(train_start, train_end)].copy()
    if train.empty or train.duplicated(["node_id", "timestamp"]).any():
        raise ValueError("Training observations missing or duplicate")
    if set(training_origins) != set(train.node_id):
        raise ValueError("Expected training origins for every training node")
    pools = {"input": [], "target": []}
    for node, group in train.groupby("node_id", sort=True):
        part = group.sort_values("timestamp").reset_index(drop=True)
        times = pd.DatetimeIndex(part.timestamp)
        origins = pd.DatetimeIndex(pd.to_datetime(training_origins[node], utc=True)).tz_convert(times.tz)
        if origins.empty:
            raise ValueError("No retained training windows for node")
        positions = times.get_indexer(origins)
        if (positions < config.lookback-1).any() or (positions+config.horizon >= len(part)).any():
            raise ValueError("Training window would cross frozen boundaries")
        if not part.timestamp.diff().iloc[1:].eq(pd.Timedelta(hours=1)).all():
            raise ValueError("Non-hourly training data")
        genuine = quality_valid(part).to_numpy()
        for role, offsets in [("input", np.arange(-config.lookback+1, 1)),
                              ("target", np.arange(1, config.horizon+1))]:
            used = np.zeros(len(part), dtype=bool)
            used[np.unique(positions[:, None]+offsets)] = True
            selected = part.loc[used & genuine, ["node_id", "timestamp", *TARGETS]].copy()
            pools[role].append(selected)
    result = {}
    for role, frames in pools.items():
        table = pd.concat(frames, ignore_index=True).sort_values(["node_id", "timestamp"]).reset_index(drop=True)
        assert not table.duplicated(["node_id", "timestamp"]).any()
        assert table.timestamp.between(train_start, train_end).all()
        result[role] = table
    return result


def fit_training_scalers(data, train_start, train_end, training_origins, config):
    pools = training_fit_observations(data, train_start, train_end, training_origins, config)
    scalers = {role: fit_standardizer(table.loc[:, TARGETS].to_numpy(),
                                    np.ones((len(table), 3), dtype=bool))
               for role, table in pools.items()}
    return scalers, pools
