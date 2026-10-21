"""Reload a frozen LSTM checkpoint and infer without compiling or training."""
import argparse
from pathlib import Path

import keras
import numpy as np

from . import model as lstm_model  # Register the saved custom Model/Metric classes.
from .evaluation import batched_predictions
from ...preprocessing.pipeline import LABEL, TARGETS
from ...common.paths import digest
from ...common.paths import SCALED_OUTPUT as DATA
from ...preprocessing.scaling import Standardizer
import json


def infer(model_path,input_path,output_path):
    model_path,input_path,output_path=map(lambda p:Path(p).resolve(),(model_path,input_path,output_path))
    if output_path.exists() or not output_path.is_relative_to(model_path.parent):
        raise ValueError('Inference output must be a NEW file inside the trained model experiment directory')
    scaler_path=model_path.parent/'scalers_frozen.json'
    if not scaler_path.exists():scaler_path=DATA/'scalers.json'
    saved=json.loads(scaler_path.read_text(encoding='utf-8'))
    target=Standardizer.from_dict(saved['target'])
    with np.load(input_path,allow_pickle=False) as z:
        if tuple(z['features'])!=TARGETS or str(z['scaler_parameters_sha256'])!=digest(scaler_path):
            raise ValueError('Input feature/scaler contract mismatch')
        x=z['X']
        if x.dtype!=np.float32 or x.shape[1:]!=(336,3) or not np.isfinite(x).all():
            raise ValueError('Expected finite float32 [N,336,3] historical input')
        origins=z['forecast_origin_unix_ns'].copy()
    model=keras.models.load_model(model_path,compile=False)
    predicted=batched_predictions(model,x,16)
    physical=target.inverse_transform(predicted,TARGETS)
    np.savez_compressed(output_path,predictions_scaled=predicted,predictions_original_units=physical,
                        forecast_origin_unix_ns=origins,targets=np.array(TARGETS),evaluation_label=np.array(LABEL))
    print(LABEL)
    print('Frozen inference only:',predicted.shape,'finite:',np.isfinite(physical).all(),'output:',output_path)


def main():
    p=argparse.ArgumentParser(description=LABEL)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();infer(a.model,a.input,a.output)


if __name__ == "__main__":
    main()
