"""Read-only synthetic history requests; never read NPZ y or expose future labels."""
from functools import lru_cache
from datetime import timedelta

import numpy as np
import pandas as pd

from ..common.paths import SOURCE, SCALED_OUTPUT, digest
from ..preprocessing.pipeline import LABEL, TARGETS, load
from .schemas import ForecastRequest, DemoInput
from .service import InvalidHistory, ModelUnavailable, load_scalers, prepare_history


@lru_cache(maxsize=1)
def _source_history():
    return load(SOURCE), digest(SOURCE)


def demo_input(model, node_id, sample_index=0):
    try:
        scalers, scaler_sha = load_scalers()
        prepared = SCALED_OUTPUT/f'windows_test_{node_id}.npz'
        with np.load(prepared, allow_pickle=False) as z:
            if (tuple(z['features']) != TARGETS or tuple(z['targets']) != TARGETS
                    or str(z['scaler_parameters_sha256']) != scaler_sha):
                raise ValueError('Prepared artifact contract mismatch')
            if not 0 <= sample_index < len(z['forecast_origin_unix_ns']):
                raise InvalidHistory('Demo sample_index must identify an existing test history window (0–810)')
            origin = pd.Timestamp(int(z['forecast_origin_unix_ns'][sample_index]),tz='UTC').tz_convert('Asia/Colombo')
            expected_x = z['X'][sample_index:sample_index+1].copy()
            expected_valid = z['history_valid_mask'][sample_index].copy()
            # Deliberately never access y, target_valid_mask or evaluation predictions.
        frame, source_sha = _source_history()
        history = frame[frame.node_id.eq(node_id) & frame.timestamp.between(origin-timedelta(hours=335),origin)].copy()
        if len(history) != 336:
            raise ValueError('Source history does not match prepared period')
        observations = []
        for row in history.itertuples():
            observations.append(dict(timestamp=row.timestamp.to_pydatetime(),
                                     **{name:float(getattr(row,name)) for name in TARGETS},
                                     record_status=row.record_status,is_anomaly=bool(row.is_anomaly),is_imputed=bool(row.is_imputed),
                                     imputed_fields=row.imputed_fields,quality_score=float(row.quality_score)))
        request = ForecastRequest(model=model,node_id=node_id,observations=observations,
                                  forecast_origin=origin.to_pydatetime(),data_origin='synthetic')
        x,valid = prepare_history(request,scalers['input'])
        np.testing.assert_array_equal(valid,expected_valid)
        np.testing.assert_array_equal(x,expected_x)
        return DemoInput(request=request,evaluation_label=LABEL,
                         demo=dict(source='Existing synthetic 2025 history; not real C1 data',source_dataset_id=SOURCE.stem,
                                   source_sha256=source_sha,prepared_artifact_id=prepared.stem,scaler_sha256=scaler_sha,
                                   split='test',sample_index=sample_index,node_id=node_id,forecast_origin=origin.isoformat(),
                                   history_records=336,ground_truth_included=False,
                                   prepared_tensor_match=True))
    except InvalidHistory:
        raise
    except Exception as exc:
        raise ModelUnavailable('Synthetic demo history is unavailable or does not match the frozen input contract') from exc
