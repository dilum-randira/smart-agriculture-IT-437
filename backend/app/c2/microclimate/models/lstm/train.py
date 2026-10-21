"""Full-cohort standard LSTM experiment, validation selection, then test evaluation."""
import argparse
import io
import json
import os
from pathlib import Path
import platform
import time
import unittest

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL","2")
import keras
import numpy as np
import pandas as pd
import tensorflow as tf

from ...preprocessing.pipeline import LABEL, TARGETS, UNITS
from ...common.paths import BACKEND, digest
from ...common.paths import SCALED_OUTPUT as DATA
from ...preprocessing.scaling import Standardizer
from .model import MaskedLSTM
from .evaluation import evaluate_forecasts, batched_predictions

DEFAULT_OUTPUT=BACKEND/'experiments/c2/microclimate/lstm_v1'
from ...common.data import EXPECTED, load_node, load_cohort


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def protected_inventory(output):
    files=[]
    for root in (BACKEND/'data/c2',BACKEND/'models/c2',BACKEND/'experiments/c2'):
        files.extend(p for p in root.rglob('*') if p.is_file() and not p.is_relative_to(output))
    return {p.relative_to(BACKEND).as_posix():digest(p) for p in sorted(files)}


def dataset(arrays,batch_size,training,seed):
    result=tf.data.Dataset.from_tensor_slices(arrays)
    if training:
        result=result.shuffle(1024,seed=seed,reshuffle_each_iteration=True)
    options=tf.data.Options()
    options.experimental_deterministic=True
    options.threading.private_threadpool_size=2
    return result.batch(batch_size,drop_remainder=False).with_options(options).prefetch(1)


class EpochEvidence(keras.callbacks.Callback):
    def __init__(self,output,config,validation_count):
        super().__init__();self.output=output;self.config=config;self.rows=[];self.validation_count=validation_count

    def on_train_begin(self,logs=None):
        self.training_start=time.perf_counter()

    def on_epoch_begin(self,epoch,logs=None):
        self.epoch_start=time.perf_counter()

    def on_epoch_end(self,epoch,logs=None):
        assert np.isfinite(logs['loss']) and np.isfinite(logs['val_loss'])
        count=int(self.model.loss_tracker.valid_count.numpy())
        assert count==self.validation_count,(count,self.validation_count)
        row=dict(epoch=epoch+1,loss=float(logs['loss']),val_loss=float(logs['val_loss']),
                 seconds=time.perf_counter()-self.epoch_start,validation_valid_elements=count,
                 evaluation_label=LABEL)
        self.rows.append(row)
        pd.DataFrame(self.rows).to_csv(self.output/'training_history.csv',index=False)
        write_json(self.output/'runtime.json',dict(status='training',completed_epochs=len(self.rows),
                   elapsed_training_seconds=time.perf_counter()-self.training_start,
                   best_epoch=min(self.rows,key=lambda r:r['val_loss'])['epoch'],evaluation_label=LABEL))
        if epoch==0:
            self.model.save(self.output/'first_epoch.keras')
        print('C2_EPOCH '+json.dumps(row),flush=True)


def preflight_tests():
    names=['app.c2.microclimate.preprocessing.tests.test_phase1','app.c2.microclimate.preprocessing.tests.test_phase1_masked',
           'app.c2.microclimate.preprocessing.tests.test_scaling','app.c2.microclimate.models.lstm.tests.test_lstm']
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in names)
    text=io.StringIO();result=unittest.TextTestRunner(stream=text,verbosity=2).run(suite)
    print(text.getvalue(),flush=True)
    if not result.wasSuccessful() or result.skipped:
        raise RuntimeError('Preflight failed; full training not started')
    return text.getvalue(),dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))


def plots(output,history,predictions):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    fig,ax=plt.subplots(figsize=(10,5))
    ax.plot(history.epoch,history.loss,label='Training masked MSE')
    ax.plot(history.epoch,history.val_loss,label='Validation masked MSE')
    best=history.loc[history.val_loss.idxmin()]
    ax.axvline(best.epoch,linestyle=':',color='gray',label=f'Best epoch {int(best.epoch)}')
    ax.set(xlabel='Completed epoch',ylabel='MSE in standardized target space',title=LABEL)
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(output/'loss_curves.png',dpi=140);plt.close(fig)
    for node,actual,lstm,persistence,mask,origins in predictions:
        dates=pd.date_range(pd.Timestamp(int(origins[0]),tz='UTC').tz_convert('Asia/Colombo')+pd.Timedelta(hours=1),periods=168,freq='h')
        fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True)
        for j,ax in enumerate(axes):
            ax.plot(dates,np.where(mask[0,:,j],actual[0,:,j],np.nan),label='Eligible synthetic actual')
            ax.plot(dates,lstm[0,:,j],label='Standard LSTM')
            ax.plot(dates,persistence[0,:,j],label='Persistence',linestyle='--',alpha=.7)
            ax.set_ylabel(f'{TARGETS[j]}\n({UNITS[j]})');ax.legend(fontsize=8);ax.grid(alpha=.2)
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M',tz=dates.tz))
        axes[-1].set_xlabel('Target timestamp — Asia/Colombo (UTC+05:30)')
        fig.suptitle(f'{LABEL}\n{node} held-out test · first chronological forecast origin')
        fig.tight_layout(rect=(0,0,1,.94));fig.savefig(output/f'forecast_{node}.png',dpi=140);plt.close(fig)


def evaluate_selected(model,output,scalers,batch_size):
    rows,leads,prediction_sets=[],[],[]
    for node in EXPECTED['test']:
        x,y,mask,origins=load_node('test',node)
        scaled=batched_predictions(model,x,batch_size)
        actual=scalers['target'].inverse_transform(y,TARGETS)  # Finite placeholders remain mask-excluded.
        prediction=scalers['target'].inverse_transform(scaled,TARGETS)
        last=scalers['input'].inverse_transform(x[:,-1:,:],TARGETS)
        persistence=np.repeat(last,168,axis=1)
        np.savez_compressed(output/f'test_predictions_{node}.npz',predictions_scaled=scaled,
                            predictions_original_units=prediction,actual_original_units=actual,
                            persistence_original_units=persistence,target_valid_mask=mask,
                            forecast_origin_unix_ns=origins,targets=np.array(TARGETS),
                            evaluation_label=np.array(LABEL),
                            actual_placeholder_warning=np.array('Values at mask=False are placeholders, not ground truth'))
        prediction_sets.append((node,actual,prediction,persistence,mask,origins))
    pooled=(np.concatenate([s[j] for s in prediction_sets]) for j in (1,2,3,4))
    actual,prediction,persistence,mask=pooled
    cohorts=[(s[0],s[1],s[2],s[3],s[4]) for s in prediction_sets]+[('POOLED',actual,prediction,persistence,mask)]
    for node,actual,prediction,persistence,mask in cohorts:
        for name,p in [('LSTM',prediction),('Persistence',persistence)]:
            r,l=evaluate_forecasts(actual,p,mask,name,node);rows.extend(r);leads.extend(l)
    metrics=pd.DataFrame(rows);pd.DataFrame(leads).to_csv(output/'test_lead_metrics.csv',index=False)
    metrics.to_csv(output/'test_metrics.csv',index=False)
    keys=['node','target','unit','window_hours']
    comparison=metrics[metrics.model.eq('LSTM')].merge(metrics[metrics.model.eq('Persistence')],on=keys,suffixes=('_lstm','_persistence'),validate='one_to_one')
    assert np.array_equal(comparison.valid_observations_lstm,comparison.valid_observations_persistence)
    comparison['MAE_improvement_percent']=100*(comparison.MAE_persistence-comparison.MAE_lstm)/comparison.MAE_persistence
    comparison['RMSE_improvement_percent']=100*(comparison.RMSE_persistence-comparison.RMSE_lstm)/comparison.RMSE_persistence
    comparison['evaluation_label']=LABEL;comparison.to_csv(output/'persistence_comparison.csv',index=False)
    # Check reference against the prior masked scaled evaluation, without changing it.
    reference=pd.read_csv(DATA/'original_unit_persistence_metrics.csv')
    for row in metrics[metrics.model.eq('Persistence') & metrics.node.ne('POOLED')].itertuples():
        ref=reference[reference.node.eq(row.node)&reference.target.eq(row.target)&reference.window_hours.eq(row.window_hours)&reference.split.eq('test')].iloc[0]
        assert row.valid_observations==ref.valid_observations
        assert abs(row.MAE-ref.MAE)<1e-5 and abs(row.RMSE-ref.RMSE)<1e-5
    return metrics,comparison,prediction_sets


def run(output=DEFAULT_OUTPUT):
    output=Path(output).resolve()
    if not output.is_relative_to((BACKEND/'experiments/c2/microclimate').resolve()) or output.exists():
        raise ValueError('Use a NEW experiment directory under experiments/c2/microclimate')
    config=dict(seed=42,units=32,lookback=336,horizon=168,features=list(TARGETS),batch_size=16,
                learning_rate=.001,optimizer='Adam',global_clipnorm=1.,maximum_epochs=100,patience=10,
                restore_best_weights=True,shuffle_buffer=1024,drop_remainder=False,
                intra_op_threads=6,inter_op_threads=1,steps_per_execution=16,jit_compile=False,
                training_samples=11137,validation_samples=1622,test_samples=1622,
                model='Standard LSTM baseline; not Attention BiLSTM',evaluation_label=LABEL)
    tf.config.set_visible_devices([], 'GPU')
    tf.config.threading.set_intra_op_parallelism_threads(6)
    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.keras.utils.set_random_seed(config['seed'])
    tf.config.experimental.enable_op_determinism()
    protected=protected_inventory(output)
    preflight_log,preflight=preflight_tests()
    train=load_cohort('train');validation=load_cohort('validation')
    assert len(train[0])==11137 and len(validation[0])==1622
    saved=json.loads((DATA/'scalers.json').read_text(encoding='utf-8'))
    scalers={role:Standardizer.from_dict(saved[role]) for role in ('input','target')}
    for role in scalers:assert scalers[role].features==TARGETS
    output.mkdir(parents=True,exist_ok=False)
    (output/'preflight_tests.txt').write_text(LABEL+'\n'+preflight_log,encoding='utf-8')
    write_json(output/'preflight_tests.json',dict(evaluation_label=LABEL,**preflight))
    write_json(output/'training_config.json',config)
    write_json(output/'input_provenance.json',dict(evaluation_label=LABEL,protected_sha256=protected,
               scaler_sha256=digest(DATA/'scalers.json'),scaled_data_directory=str(DATA),
               frozen_splits=json.loads((DATA/'validation_report.json').read_text(encoding='utf-8'))['splits'],
               python=platform.python_version(),tensorflow=tf.__version__,keras=keras.__version__,numpy=np.__version__))
    model=MaskedLSTM(name='c2_standard_lstm')
    first=model(train[0][:2],training=False)
    assert first.shape==(2,168,3) and np.isfinite(first.numpy()).all()
    assert model.forecaster.count_params()==13027
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=.001,global_clipnorm=1.),
                  jit_compile=False,steps_per_execution=16)
    summary=[];model.forecaster.summary(print_fn=lambda line:summary.append(line))
    (output/'architecture.txt').write_text(LABEL+'\n'+'\n'.join(summary)+'\n',encoding='utf-8')
    train_ds=dataset(train,16,True,42);validation_ds=dataset(validation,16,False,42)
    evidence=EpochEvidence(output,config,int(validation[2].sum()))
    callbacks=[evidence,
               keras.callbacks.ModelCheckpoint(output/'best_validation.keras',monitor='val_loss',mode='min',save_best_only=True),
               keras.callbacks.EarlyStopping(monitor='val_loss',mode='min',patience=10,restore_best_weights=True),
               keras.callbacks.TerminateOnNaN()]
    print('FULL_TRAINING_START '+json.dumps(config),flush=True)
    start=time.perf_counter()
    model.fit(train_ds,validation_data=validation_ds,epochs=100,callbacks=callbacks,verbose=0)
    duration=time.perf_counter()-start
    history=pd.DataFrame(evidence.rows)
    if not len(history):raise RuntimeError('No epoch completed')
    best=history.loc[history.val_loss.idxmin()]
    # Complete validation-only selection before trained-model test inference.
    selected=keras.models.load_model(output/'best_validation.keras',compile=False)
    restored_prediction=selected(validation[0][:2],training=False).numpy()
    expected_prediction=model(validation[0][:2],training=False).numpy()
    np.testing.assert_allclose(restored_prediction,expected_prediction,rtol=0,atol=1e-6)
    selected.save(output/'lstm_best.keras')
    reloaded=keras.models.load_model(output/'lstm_best.keras',compile=False)
    np.testing.assert_allclose(reloaded(validation[0][:2],training=False).numpy(),restored_prediction,rtol=0,atol=1e-6)
    metrics,comparison,predictions=evaluate_selected(reloaded,output,scalers,16)
    plots(output,history,predictions)
    assert protected_inventory(output)==protected,'Upstream artifacts changed'
    report=dict(evaluation_label=LABEL,status='complete',epochs_completed=len(history),best_epoch=int(best.epoch),
                training_duration_seconds=duration,mean_epoch_seconds=float(history.seconds.mean()),
                best_epoch_training_loss=float(best.loss),best_validation_loss=float(best.val_loss),
                last_epoch_training_loss=float(history.loss.iloc[-1]),last_epoch_validation_loss=float(history.val_loss.iloc[-1]),
                stopped_early=len(history)<100,maximum_epochs=100,patience=10,parameters=13027,
                preflight_tests=preflight,trained_model='lstm_best.keras',reload_max_absolute_error=float(np.max(np.abs(restored_prediction-expected_prediction))),
                input_files_unchanged=True,validation_only_model_selection=True,
                heldout_test_evaluated_after_selection=True,physical_units=list(UNITS),
                limitations=['100% synthetic; no real Sri Lankan Nai Miris field validation.',
                             'Overlapping forecast origins are dependent; counts are repeated observation/forecast pairs.',
                             'Quality filtering and stale historical fills remain limitations.',
                             'R2 is unavailable for fewer than two valid values or constant actuals.',
                             'This is one fixed baseline configuration, not a tuned or statistically proven winner.'])
    write_json(output/'training_report.json',report);write_json(output/'runtime.json',report)
    write_json(output/'preservation_verification.json',dict(evaluation_label=LABEL,files_checked=len(protected),unchanged=True))
    from .reporting import write_reports
    write_reports(output)
    print('FULL_TRAINING_COMPLETE '+json.dumps(report),flush=True)
    print(metrics.to_string(index=False),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=LABEL)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    run(parser.parse_args().output)


if __name__ == "__main__":
    main()
