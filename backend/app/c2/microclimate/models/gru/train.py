"""Full fixed-protocol GRU training; held-out evaluation only after selection."""
import argparse
import io
import json
import platform
import time
import unittest
from pathlib import Path

import keras
import numpy as np
import pandas as pd
import tensorflow as tf

from ...common.data import DATA, load_cohort
from ...common.paths import BACKEND, digest
from ...preprocessing.pipeline import LABEL, TARGETS, UNITS
from ...preprocessing.scaling import Standardizer
from ..lstm.train import EpochEvidence, dataset, protected_inventory, write_json
from .model import MaskedGRU
from .evaluation import evaluate_selected

DEFAULT_OUTPUT = BACKEND/'experiments/c2/microclimate/gru_v1'


def preflight_tests():
    suite = unittest.defaultTestLoader.discover(str(BACKEND/'app/c2/microclimate'), top_level_dir=str(BACKEND))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    print(stream.getvalue(), flush=True)
    if not result.wasSuccessful() or result.skipped:
        raise RuntimeError('GRU preflight failed; research training not started')
    return stream.getvalue(), dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped))


def run(output=DEFAULT_OUTPUT):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to((BACKEND/'experiments/c2/microclimate').resolve()):
        raise ValueError('Use a NEW experiment directory under experiments/c2/microclimate')
    config = dict(seed=42, units=32, lookback=336, horizon=168, features=list(TARGETS),
                  batch_size=16, learning_rate=.001, optimizer='Adam', global_clipnorm=1.,
                  maximum_epochs=100, patience=10, restore_best_weights=True,
                  shuffle_buffer=1024, drop_remainder=False, intra_op_threads=6,
                  inter_op_threads=1, steps_per_execution=16, jit_compile=False,
                  training_samples=11137, validation_samples=1622, test_samples=1622,
                  gru_reset_after=True, model='Standard GRU baseline; not Attention BiLSTM', evaluation_label=LABEL)
    tf.config.set_visible_devices([], 'GPU')
    tf.config.threading.set_intra_op_parallelism_threads(6)
    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.keras.utils.set_random_seed(42)
    tf.config.experimental.enable_op_determinism()
    protected = protected_inventory(output)
    preflight_log, preflight = preflight_tests()
    # Preflight fixture randomness cannot determine the research initialization.
    tf.keras.utils.set_random_seed(42)
    train = load_cohort('train'); validation = load_cohort('validation')
    assert train[0].shape == (11137,336,3) and train[1].shape == (11137,168,3)
    assert validation[0].shape == (1622,336,3)
    frozen = json.loads((DATA/'scalers.json').read_text(encoding='utf-8'))
    scalers = {role: Standardizer.from_dict(frozen[role]) for role in ('input','target')}
    assert all(s.features == TARGETS for s in scalers.values())
    output.mkdir(parents=True, exist_ok=False)
    (output/'preflight_tests.txt').write_text(LABEL+'\n'+preflight_log, encoding='utf-8')
    write_json(output/'preflight_tests.json', dict(evaluation_label=LABEL, **preflight))
    write_json(output/'training_config.json', config)
    write_json(output/'input_provenance.json', dict(evaluation_label=LABEL, protected_sha256=protected,
               scaler_sha256=digest(DATA/'scalers.json'), scaled_data_directory=str(DATA),
               frozen_splits=json.loads((DATA/'validation_report.json').read_text(encoding='utf-8'))['splits'],
               python=platform.python_version(), tensorflow=tf.__version__, keras=keras.__version__, numpy=np.__version__,
               source_sha256={p.relative_to(BACKEND).as_posix():digest(p) for p in (BACKEND/'app/c2/microclimate').rglob('*.py')}))
    (output/'scalers_frozen.json').write_bytes((DATA/'scalers.json').read_bytes())
    model = MaskedGRU(name='c2_standard_gru')
    first = model(train[0][:2], training=False).numpy()
    assert first.shape == (2,168,3) and np.isfinite(first).all()
    assert model.forecaster.count_params() == 9987
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=.001, global_clipnorm=1.),
                  jit_compile=False, steps_per_execution=16)
    summary=[]; model.forecaster.summary(print_fn=lambda line:summary.append(line))
    (output/'architecture.txt').write_text(LABEL+'\n'+'\n'.join(summary)+'\n', encoding='utf-8')
    evidence = EpochEvidence(output, config, int(validation[2].sum()))
    callbacks = [evidence,
                 keras.callbacks.ModelCheckpoint(output/'best_validation.keras', monitor='val_loss', mode='min', save_best_only=True),
                 keras.callbacks.EarlyStopping(monitor='val_loss', mode='min', patience=10, restore_best_weights=True),
                 keras.callbacks.TerminateOnNaN()]
    print('GRU_FULL_TRAINING_START '+json.dumps(config), flush=True)
    start=time.perf_counter()
    model.fit(dataset(train,16,True,42), validation_data=dataset(validation,16,False,42),
              epochs=100, callbacks=callbacks, verbose=0)
    duration=time.perf_counter()-start
    history=pd.DataFrame(evidence.rows)
    if history.empty or not np.isfinite(history[['loss','val_loss']].to_numpy()).all():
        raise RuntimeError('GRU training did not complete with finite losses')
    if len(history)<100 and len(history)-int(history.loc[history.val_loss.idxmin(),'epoch'])<10:
        raise RuntimeError('Training ended before configured stopping criterion')
    best=history.loc[history.val_loss.idxmin()]
    selected=keras.models.load_model(output/'best_validation.keras', compile=False)
    reference=model(validation[0][:2],training=False).numpy()
    selected_prediction=selected(validation[0][:2],training=False).numpy()
    np.testing.assert_allclose(selected_prediction,reference,rtol=0,atol=1e-6)
    selected.save(output/'gru_best.keras')
    reloaded=keras.models.load_model(output/'gru_best.keras',compile=False)
    np.testing.assert_allclose(reloaded(validation[0][:2],training=False).numpy(),selected_prediction,rtol=0,atol=1e-6)
    metrics, comparison, predictions=evaluate_selected(reloaded,output,scalers,16)
    from .reporting import plots, write_reports
    plots(output,history,predictions)
    assert protected_inventory(output)==protected,'Protected upstream files changed'
    report=dict(evaluation_label=LABEL,status='complete',epochs_completed=len(history),best_epoch=int(best.epoch),
                training_duration_seconds=duration,mean_epoch_seconds=float(history.seconds.mean()),
                best_epoch_training_loss=float(best.loss),best_validation_loss=float(best.val_loss),
                minimum_training_loss=float(history.loss.min()),last_epoch_training_loss=float(history.loss.iloc[-1]),
                last_epoch_validation_loss=float(history.val_loss.iloc[-1]),stopped_early=len(history)<100,
                maximum_epochs=100,patience=10,parameters=9987,preflight_tests=preflight,
                trained_model='gru_best.keras',reload_max_absolute_error=float(np.max(np.abs(reference-selected_prediction))),
                input_files_unchanged=True,validation_only_model_selection=True,heldout_test_evaluated_after_selection=True,
                physical_units=list(UNITS),limitations=[
                    '100% synthetic; no real Sri Lankan Nai Miris field validation.',
                    'Overlapping origins are dependent forecast/observation pairs.',
                    'Single fixed seed/configuration; no significance or generalization claim.',
                    'Existing test results have already been inspected for LSTM; this is comparative prototype evidence.',
                    'Missing future irrigation/weather and stale historical fills limit forecasts.'])
    write_json(output/'training_report.json',report);write_json(output/'runtime.json',report)
    write_json(output/'preservation_verification.json',dict(evaluation_label=LABEL,files_checked=len(protected),unchanged=True))
    write_reports(output)
    print('GRU_FULL_TRAINING_COMPLETE '+json.dumps(report),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=LABEL)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    run(parser.parse_args().output)


if __name__=='__main__':
    main()
