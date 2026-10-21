"""Lazy frozen-model inference with the verified quality and scaler contracts."""
from dataclasses import dataclass, field
from datetime import timedelta
from importlib import import_module
import json
import logging
from threading import Lock

import numpy as np
import pandas as pd

from ..common.paths import BACKEND, SCALED_OUTPUT, digest
from ..preprocessing.pipeline import LABEL, TARGETS, quality_valid
from ..preprocessing.scaling import Standardizer
from .schemas import ForecastRequest, ForecastResponse, HistorySummary, Provenance

logger = logging.getLogger(__name__)
SCALER_PATH = SCALED_OUTPUT/'scalers.json'
MODEL_SPECS = {
    'lstm': ('lstm_v1', 'lstm_best.keras', 'app.c2.microclimate.models.lstm.model', 13027),
    'gru': ('gru_v1', 'gru_best.keras', 'app.c2.microclimate.models.gru.model', 9987),
    'attention_bilstm': ('attention_bilstm_v1', 'attention_bilstm_best.keras', 'app.c2.microclimate.models.attention_bilstm.model', 30040),
}
QUALITY_POLICY = ('INVALID/anomalous/supplied-imputed rows are excluded as observations and all three inputs '
                  'are causally forward-filled within supplied history. Clean WARN is retained. No backward fill, '
                  'interpolation or scaler fitting. Missing/nonfinite values and leading untrusted history are rejected. '
                  'Omitted quality flags are caller assertions of usable data, not independently verified quality.')


class InvalidHistory(ValueError):
    pass


class ModelUnavailable(RuntimeError):
    pass


class InferenceFailure(RuntimeError):
    pass


@dataclass
class Runtime:
    model: object
    input_scaler: Standardizer
    target_scaler: Standardizer
    checkpoint_sha256: str
    scaler_sha256: str
    artifact_id: str
    inference_lock: Lock = field(default_factory=Lock)


_runtimes: dict[str, Runtime] = {}
_load_lock = Lock()


def load_scalers():
    saved = json.loads(SCALER_PATH.read_text(encoding='utf-8'))
    if saved['evaluation_label'] != LABEL:
        raise ValueError('Unsupported scaler provenance')
    scalers = {role: Standardizer.from_dict(saved[role]) for role in ('input','target')}
    if any(s.features != TARGETS for s in scalers.values()):
        raise ValueError('Unsupported feature order')
    return scalers, digest(SCALER_PATH)


def get_runtime(model_id):
    """Exactly one cached load per selected model, including concurrent first calls."""
    with _load_lock:
        if model_id in _runtimes:
            return _runtimes[model_id]
        try:
            folder, filename, module, parameters = MODEL_SPECS[model_id]
            root = BACKEND/'experiments/c2/microclimate'/folder
            checkpoint = root/filename
            scalers, scaler_sha = load_scalers()
            provenance = json.loads((root/'input_provenance.json').read_text(encoding='utf-8'))
            report = json.loads((root/'training_report.json').read_text(encoding='utf-8'))
            if (provenance['scaler_sha256'] != scaler_sha or digest(root/'scalers_frozen.json') != scaler_sha
                    or report['status'] != 'complete' or report['evaluation_label'] != LABEL):
                raise ValueError('Frozen artifact provenance mismatch')
            import_module(module)  # Registers only the requested custom model and its dependencies.
            import keras
            import tensorflow as tf
            # CPU resource controls only; never alter architecture, weights or optimizer.
            try:
                tf.config.threading.set_intra_op_parallelism_threads(6)
                tf.config.threading.set_inter_op_parallelism_threads(1)
            except RuntimeError:
                logger.info('TensorFlow already initialized; retaining existing thread configuration')
            with tf.device('/CPU:0'):
                model = keras.models.load_model(checkpoint, compile=False)
            if (model.forecaster.input_shape != (None,336,3) or model.forecaster.output_shape != (None,168,3)
                    or model.forecaster.count_params() != parameters):
                raise ValueError('Unexpected trained-model contract')
            runtime = Runtime(model, scalers['input'], scalers['target'], digest(checkpoint), scaler_sha,
                              f'c2_microclimate_{folder}')
            _runtimes[model_id] = runtime
            return runtime
        except Exception as exc:
            logger.exception('Unable to load selected frozen microclimate runtime: %s', model_id)
            raise ModelUnavailable('Selected model is unavailable; check server artifacts and configuration') from exc


def prepare_history(request: ForecastRequest, input_scaler: Standardizer):
    frame = pd.DataFrame([row.model_dump() for row in request.observations])
    valid = quality_valid(frame).to_numpy(dtype=bool)
    raw = frame.loc[:, TARGETS].to_numpy(dtype=np.float64)
    if not valid[0]:
        raise InvalidHistory('The first historical observation must be usable: earlier context is unavailable for causal filling')
    # Same row-level masking and causal ffill as preprocessing.pipeline._window_arrays.
    filled = pd.DataFrame(np.where(valid[:,None],raw,np.nan)).ffill().to_numpy()
    try:
        x = input_scaler.transform(filled[None,...], TARGETS)
    except ValueError as exc:
        raise InvalidHistory('Historical values cannot be represented by the saved input scaler') from exc
    if x.shape != (1,336,3) or x.dtype != np.float32 or not np.isfinite(x).all():
        raise InvalidHistory('Expected finite float32 [1,336,3] historical input')
    return x, valid


def forecast(request: ForecastRequest):
    # Validate unsupported leading history before expensive model loading.
    first = request.observations[0]
    if first.record_status == 'INVALID' or first.is_anomaly or first.is_imputed:
        raise InvalidHistory('The first historical observation must be usable: earlier context is unavailable for causal filling')
    runtime = get_runtime(request.model)
    x, valid = prepare_history(request, runtime.input_scaler)
    try:
        import tensorflow as tf
        with runtime.inference_lock, tf.device('/CPU:0'):
            scaled = runtime.model(x, training=False).numpy()
        if scaled.shape != (1,168,3) or not np.isfinite(scaled).all():
            raise ValueError('Invalid forecast tensor')
        physical = runtime.target_scaler.inverse_transform(scaled, TARGETS)[0]
        if not np.isfinite(physical).all():
            raise ValueError('Nonfinite original-unit forecast')
    except Exception as exc:
        logger.exception('Frozen microclimate inference failed: %s', request.model)
        raise InferenceFailure('Forecast inference failed; consult the server log') from exc
    origin = request.observations[-1].timestamp
    predictions = [dict(lead_hour=h, timestamp=origin+timedelta(hours=h),
                        **{target: float(physical[h-1,j]) for j,target in enumerate(TARGETS)}) for h in range(1,169)]
    quality_fields = {'record_status','is_anomaly','is_imputed','imputed_fields','quality_score'}
    return ForecastResponse(
        model=request.model, node_id=request.node_id, forecast_origin=origin,
        feature_order=list(TARGETS), target_order=list(TARGETS),
        units=dict(zip(TARGETS, ('INDEX (not calibrated volumetric water content)','°C','% RH'))),
        history=HistorySummary(start=request.observations[0].timestamp,end=origin,
                               eligible_under_declared_quality=int(valid.sum()),causally_filled_rows=int((~valid).sum()),
                               history_valid_mask=valid.tolist(),quality_policy=QUALITY_POLICY,
                               quality_metadata_rows=sum(bool(quality_fields & row.model_fields_set) for row in request.observations)),
        predictions=predictions,
        slices=[dict(hours=h,end_index_exclusive=h,first_timestamp=predictions[0]['timestamp'],
                     last_timestamp=predictions[h-1]['timestamp']) for h in (24,72,168)],
        provenance=Provenance(model_artifact_id=runtime.artifact_id,checkpoint_sha256=runtime.checkpoint_sha256,
                              scaler_artifact_id='c2_microclimate_phase1_masked_scaled',scaler_sha256=runtime.scaler_sha256,
                              training_data='100% synthetic hourly 2025 data; two nodes; no real C1 field validation',
                              scaler_fit_policy='Frozen, per-feature scalers fitted on unique genuine TRAIN observations only; never refitted by API',
                              inference_mode='CPU; frozen checkpoint; compile=False; training=False',declared_input_origin=request.data_origin,
                              limitations=['Prototype predictions do not establish real Nai Miris field accuracy.',
                                           'Quality flags are supplied by the caller; omitted flags assert usable observations.',
                                           'Unknown future irrigation/weather and stale historical fills limit forecasts.']),
        evaluation_label=LABEL)
