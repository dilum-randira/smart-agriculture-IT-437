"""Four-model evaluation and fixed chronological descriptive attention examples."""
import numpy as np
import pandas as pd

from ...common.comparison import compare_forecasts
from ...common.data import DATA, load_node
from ...common.paths import BACKEND
from ...preprocessing.pipeline import LABEL

MODEL_NAME='AttentionBiLSTM'
REFERENCES={name:BACKEND/f'experiments/c2/microclimate/{folder}' for name,folder in [('LSTM','lstm_v1'),('GRU','gru_v1')]}


def evaluate_selected(model,output,scalers,batch_size=16):
    result=compare_forecasts(model,output,scalers,MODEL_NAME,REFERENCES,batch_size)
    for s in result[2]:
        x,_,_,origins=load_node('test',s['node'])
        # Fixed first chronological origin; never selected by held-out error/attention.
        weights=model.attention_weights(x[:1]).numpy()
        assert weights.shape==(1,336) and np.isfinite(weights).all() and (weights>=0).all()
        np.testing.assert_allclose(weights.sum(axis=1),1.,rtol=0,atol=1e-6)
        timestamps=origins[0]-np.arange(335,-1,-1,dtype=np.int64)*3600*10**9
        with np.load(DATA/f"windows_test_{s['node']}.npz",allow_pickle=False) as z:
            history_valid=z['history_valid_mask'][:1].copy()
        np.savez_compressed(output/f"attention_{s['node']}.npz",weights=weights,historical_inputs_scaled=x[:1],
                            historical_timestamps_unix_ns=timestamps,forecast_origin_unix_ns=origins[:1],
                            history_valid_mask=history_valid,evaluation_label=np.array(LABEL),
                            interpretation=np.array('Descriptive historical temporal attention; not causal explanation'))
        pd.DataFrame(dict(node=s['node'],historical_timestamp=pd.to_datetime(timestamps,utc=True).tz_convert('Asia/Colombo').astype(str),
                          attention_weight=weights[0],original_history_valid=history_valid[0],
                          interpretation='Descriptive, not causal',evaluation_label=LABEL)).to_csv(output/f"attention_{s['node']}.csv",index=False)
    return result
