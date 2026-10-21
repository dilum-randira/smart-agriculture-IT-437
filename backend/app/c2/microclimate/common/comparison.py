"""Frozen-reference multi-model evaluation on identical eligible target positions."""
import numpy as np
import pandas as pd

from .data import EXPECTED, load_node
from ..preprocessing.pipeline import LABEL, TARGETS
from ..models.lstm.evaluation import batched_predictions, evaluate_forecasts
from ..models.gru.evaluation import assert_comparable


def compare_forecasts(model, output, scalers, current_name, references, batch_size=16):
    sets=[]
    for node in EXPECTED['test']:
        x,y,mask,origins=load_node('test',node)
        scaled=batched_predictions(model,x,batch_size)
        actual=scalers['target'].inverse_transform(y,TARGETS)
        prediction=scalers['target'].inverse_transform(scaled,TARGETS)
        persistence=np.repeat(scalers['input'].inverse_transform(x[:,-1:,:],TARGETS),168,axis=1)
        forecasts={'Persistence':persistence}
        for name,path in references.items():
            with np.load(path/f'test_predictions_{node}.npz',allow_pickle=False) as ref:
                assert_comparable(actual,persistence,mask,origins,ref)
                forecasts[name]=ref['predictions_original_units'].copy()
        forecasts[current_name]=prediction
        np.savez_compressed(output/f'test_predictions_{node}.npz',predictions_scaled=scaled,
                            predictions_original_units=prediction,actual_original_units=actual,
                            persistence_original_units=persistence,target_valid_mask=mask,
                            forecast_origin_unix_ns=origins,targets=np.array(TARGETS),evaluation_label=np.array(LABEL),
                            actual_placeholder_warning=np.array('mask=False actuals are placeholders, not ground truth'))
        sets.append(dict(node=node,actual=actual,mask=mask,origins=origins,forecasts=forecasts))
    pooled=dict(node='POOLED',actual=np.concatenate([s['actual'] for s in sets]),mask=np.concatenate([s['mask'] for s in sets]),
                forecasts={name:np.concatenate([s['forecasts'][name] for s in sets]) for name in sets[0]['forecasts']})
    rows,leads=[],[]
    for s in sets+[pooled]:
        for name,prediction in s['forecasts'].items():
            r,l=evaluate_forecasts(s['actual'],prediction,s['mask'],name,s['node'])
            rows.extend(r);leads.extend(l)
    metrics=pd.DataFrame(rows);metrics.to_csv(output/'test_metrics.csv',index=False)
    pd.DataFrame(leads).to_csv(output/'test_lead_metrics.csv',index=False)
    keys=['node','target','unit','window_hours']
    comparison=None
    for name in sets[0]['forecasts']:
        part=metrics[metrics.model.eq(name)].drop(columns='model')
        part=part.rename(columns={c:f'{c}_{name}' for c in part.columns if c not in keys})
        comparison=part if comparison is None else comparison.merge(part,on=keys,validate='one_to_one')
    for name in sets[0]['forecasts']:
        np.testing.assert_array_equal(comparison[f'valid_observations_{name}'],comparison['valid_observations_Persistence'])
    names=list(sets[0]['forecasts'])
    for metric,minimum in [('RMSE',True),('MAE',True),('R2',False)]:
        values=comparison[[f'{metric}_{n}' for n in names]].to_numpy()
        best=np.nanmin(values,axis=1) if minimum else np.nanmax(values,axis=1)
        comparison[f'{metric}_winner']=[', '.join(n for n,v in zip(names,row) if np.isclose(v,b,rtol=0,atol=1e-12)) or 'unavailable' for row,b in zip(values,best)]
    comparison['evaluation_label']=LABEL
    comparison.to_csv(output/'four_model_comparison.csv',index=False)
    # Independently reproduce all immutable baseline aggregate metrics.
    for name,path in references.items():
        original=pd.read_csv(path/'test_metrics.csv')
        for row in metrics[metrics.model.eq(name)].itertuples():
            ref=original[original.model.eq(name)&original.node.eq(row.node)&original.target.eq(row.target)&original.window_hours.eq(row.window_hours)].iloc[0]
            assert row.valid_observations==ref.valid_observations
            for key in ('MAE','RMSE','R2'):np.testing.assert_allclose(getattr(row,key),ref[key],rtol=0,atol=1e-9)
    return metrics,comparison,sets
