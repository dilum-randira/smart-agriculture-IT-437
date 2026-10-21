"""Frozen scaled dataset contract shared by forecast models."""
import numpy as np
from ..preprocessing.pipeline import TARGETS
from .paths import SCALED_OUTPUT as DATA
from .paths import digest

EXPECTED={'train':{'NODE_01':5629,'NODE_02':5508},'validation':{'NODE_01':811,'NODE_02':811},'test':{'NODE_01':811,'NODE_02':811}}


def load_node(split,node):
    with np.load(DATA/f'windows_{split}_{node}.npz',allow_pickle=False) as z:
        assert tuple(z['features'])==tuple(z['targets'])==TARGETS
        assert str(z['scaler_parameters_sha256'])==digest(DATA/'scalers.json')
        x,y,mask=z['X'],z['y'],z['target_valid_mask']
        assert x.shape==(EXPECTED[split][node],336,3) and y.shape==(len(x),168,3)
        assert x.dtype==y.dtype==np.float32 and mask.dtype==np.bool_ and mask.shape==y.shape
        assert np.isfinite(x).all() and np.isfinite(y).all()
        assert (mask.sum(axis=1)>=160).all() and (y[~mask]==0).all()
        return x,y,mask,z['forecast_origin_unix_ns'].copy()


def load_cohort(split):
    parts=[load_node(split,node) for node in EXPECTED[split]]
    return tuple(np.concatenate([p[j] for p in parts],axis=0) for j in (0,1,2))


