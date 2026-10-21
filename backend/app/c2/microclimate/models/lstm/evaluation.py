"""Original-unit masked metrics; pooling concatenates observations, not scores."""
import numpy as np
from ...preprocessing.pipeline import TARGETS, UNITS, LABEL


def metric_row(actual, predicted, mask):
    if actual.shape != predicted.shape or actual.shape != mask.shape:
        raise ValueError("Evaluation shapes differ")
    if mask.dtype != np.bool_:
        raise ValueError("Boolean observation mask required")
    a, p = actual[mask], predicted[mask]
    if not np.isfinite(a).all() or not np.isfinite(p).all():
        raise ValueError("Non-finite eligible evaluation values")
    count = len(a)
    error = p-a
    sse = float(np.square(error).sum())
    sst = float(np.square(a-a.mean()).sum()) if count else 0.
    return dict(valid_observations=count, possible_observations=int(mask.size),
                masked_observations=int(mask.size-count), samples=len(actual),
                contributing_samples=int(mask.reshape(len(actual),-1).any(axis=1).sum()) if len(actual) else 0,
                MAE=float(np.abs(error).mean()) if count else None,
                RMSE=float(np.sqrt(sse/count)) if count else None,
                R2=1-sse/sst if count>=2 and sst>0 else None,
                evaluation_label=LABEL)


def evaluate_forecasts(actual, predicted, mask, model, node):
    if actual.ndim != 3 or actual.shape[1:] != (168,3):
        raise ValueError("Expected [N,168,3] forecasts")
    rows, leads = [], []
    for j, target in enumerate(TARGETS):
        for horizon in (24,72,168):
            rows.append(dict(model=model,node=node,target=target,unit=UNITS[j],window_hours=horizon,
                             **metric_row(actual[:,:horizon,j],predicted[:,:horizon,j],mask[:,:horizon,j])))
        for h in range(168):
            leads.append(dict(model=model,node=node,target=target,unit=UNITS[j],lead_hour=h+1,
                              **metric_row(actual[:,h:h+1,j],predicted[:,h:h+1,j],mask[:,h:h+1,j])))
    return rows, leads


def batched_predictions(model, x, batch_size=16):
    result = np.empty((len(x),168,3), dtype=np.float32)
    for start in range(0,len(x),batch_size):
        result[start:start+batch_size] = model(x[start:start+batch_size],training=False).numpy()
    if not np.isfinite(result).all():
        raise ValueError("Non-finite predictions")
    return result
