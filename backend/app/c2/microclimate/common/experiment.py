"""Reusable fixed-protocol experiment orchestration; existing baselines untouched."""
import json
import platform
import time
from pathlib import Path

import keras
import numpy as np
import pandas as pd
import tensorflow as tf

from .data import DATA, load_cohort
from .paths import BACKEND, digest
from ..preprocessing.pipeline import LABEL, TARGETS, UNITS
from ..preprocessing.scaling import Standardizer
from ..models.lstm.train import EpochEvidence, dataset, protected_inventory, write_json
from ..models.gru.train import preflight_tests


def run_experiment(output, config, model_factory, expected_parameters, checkpoint_name,
                   evaluate_selected, plots, write_reports, sanity_check):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to((BACKEND/'experiments/c2/microclimate').resolve()):
        raise ValueError('Use a NEW experiment directory under experiments/c2/microclimate')
    tf.config.set_visible_devices([], 'GPU')
    tf.config.threading.set_intra_op_parallelism_threads(config['intra_op_threads'])
    tf.config.threading.set_inter_op_parallelism_threads(config['inter_op_threads'])
    tf.keras.utils.set_random_seed(config['seed'])
    tf.config.experimental.enable_op_determinism()
    protected = protected_inventory(output)
    preflight_log, preflight = preflight_tests()
    tf.keras.utils.set_random_seed(config['seed'])
    train=load_cohort('train');validation=load_cohort('validation')
    assert train[0].shape==(11137,336,3) and train[1].shape==(11137,168,3)
    assert validation[0].shape==(1622,336,3)
    frozen=json.loads((DATA/'scalers.json').read_text(encoding='utf-8'))
    scalers={role:Standardizer.from_dict(frozen[role]) for role in ('input','target')}
    assert all(s.features==TARGETS for s in scalers.values())
    output.mkdir(parents=True,exist_ok=False)
    (output/'preflight_tests.txt').write_text(LABEL+'\n'+preflight_log,encoding='utf-8')
    write_json(output/'preflight_tests.json',dict(evaluation_label=LABEL,**preflight))
    write_json(output/'training_config.json',config)
    write_json(output/'input_provenance.json',dict(evaluation_label=LABEL,protected_sha256=protected,
               scaler_sha256=digest(DATA/'scalers.json'),scaled_data_directory=str(DATA),
               frozen_splits=json.loads((DATA/'validation_report.json').read_text(encoding='utf-8'))['splits'],
               python=platform.python_version(),tensorflow=tf.__version__,keras=keras.__version__,numpy=np.__version__,
               source_sha256={p.relative_to(BACKEND).as_posix():digest(p) for p in (BACKEND/'app/c2/microclimate').rglob('*.py')}))
    (output/'scalers_frozen.json').write_bytes((DATA/'scalers.json').read_bytes())
    model=model_factory()
    initial=model(train[0][:2],training=False).numpy()
    assert initial.shape==(2,168,3) and np.isfinite(initial).all()
    assert model.forecaster.count_params()==expected_parameters
    write_json(output/'model_sanity.json',dict(evaluation_label=LABEL,**sanity_check(model,train)))
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=config['learning_rate'],global_clipnorm=config['global_clipnorm']),
                  jit_compile=False,steps_per_execution=config['steps_per_execution'])
    summary=[];model.forecaster.summary(print_fn=lambda line:summary.append(line))
    (output/'architecture.txt').write_text(LABEL+'\n'+'\n'.join(summary)+'\n',encoding='utf-8')
    evidence=EpochEvidence(output,config,int(validation[2].sum()))
    callbacks=[evidence,
               keras.callbacks.ModelCheckpoint(output/'best_validation.keras',monitor='val_loss',mode='min',save_best_only=True),
               keras.callbacks.EarlyStopping(monitor='val_loss',mode='min',patience=config['patience'],restore_best_weights=True),
               keras.callbacks.TerminateOnNaN()]
    print('FULL_TRAINING_START '+json.dumps(config),flush=True)
    start=time.perf_counter()
    model.fit(dataset(train,config['batch_size'],True,config['seed']),
              validation_data=dataset(validation,config['batch_size'],False,config['seed']),
              epochs=config['maximum_epochs'],callbacks=callbacks,verbose=0)
    duration=time.perf_counter()-start
    history=pd.DataFrame(evidence.rows)
    if history.empty or not np.isfinite(history[['loss','val_loss']].to_numpy()).all():
        raise RuntimeError('Training did not finish with finite losses')
    best=history.loc[history.val_loss.idxmin()]
    if len(history)<config['maximum_epochs'] and len(history)-int(best.epoch)<config['patience']:
        raise RuntimeError('Stopped before configured criterion')
    selected=keras.models.load_model(output/'best_validation.keras',compile=False)
    expected=model(validation[0][:2],training=False).numpy()
    actual=selected(validation[0][:2],training=False).numpy()
    np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-6)
    selected.save(output/checkpoint_name)
    reloaded=keras.models.load_model(output/checkpoint_name,compile=False)
    np.testing.assert_allclose(reloaded(validation[0][:2],training=False).numpy(),actual,rtol=0,atol=1e-6)
    # No trained-model test inference takes place before validation-only selection.
    metrics,comparison,predictions=evaluate_selected(reloaded,output,scalers,config['batch_size'])
    plots(output,history,predictions)
    assert protected_inventory(output)==protected,'Protected upstream artifacts changed'
    report=dict(evaluation_label=LABEL,status='complete',epochs_completed=len(history),best_epoch=int(best.epoch),
                training_duration_seconds=duration,mean_epoch_seconds=float(history.seconds.mean()),
                best_epoch_training_loss=float(best.loss),best_validation_loss=float(best.val_loss),
                minimum_training_loss=float(history.loss.min()),last_epoch_training_loss=float(history.loss.iloc[-1]),
                last_epoch_validation_loss=float(history.val_loss.iloc[-1]),stopped_early=len(history)<config['maximum_epochs'],
                maximum_epochs=config['maximum_epochs'],patience=config['patience'],parameters=expected_parameters,
                preflight_tests=preflight,trained_model=checkpoint_name,
                reload_max_absolute_error=float(np.max(np.abs(actual-expected))),input_files_unchanged=True,
                validation_only_model_selection=True,heldout_test_evaluated_after_selection=True,physical_units=list(UNITS),
                limitations=['100% synthetic; no real Sri Lankan Nai Miris field validation.',
                             'Attention is descriptive, not causal or independent proof of explainability.',
                             'Overlapping origins are dependent forecast/observation pairs.',
                             'Single fixed configuration/seed; repeated use of the same test is not external validation.',
                             'Historical forward fills and unknown future irrigation/weather limit interpretation.'])
    write_json(output/'training_report.json',report);write_json(output/'runtime.json',report)
    write_json(output/'preservation_verification.json',dict(evaluation_label=LABEL,files_checked=len(protected),unchanged=True))
    write_reports(output)
    print('FULL_TRAINING_COMPLETE '+json.dumps(report),flush=True)
    return report
