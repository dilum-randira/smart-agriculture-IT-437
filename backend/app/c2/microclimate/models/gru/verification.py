"""Fresh-process saved GRU replay and independent evaluation verification."""
import argparse
import io
import json
from pathlib import Path
import unittest
import zipfile

import h5py
import keras
import numpy as np
import pandas as pd
import tensorflow as tf

from . import model
from .evaluation import LSTM_OUTPUT, assert_comparable
from ...common.data import DATA, EXPECTED, load_node
from ...common.paths import BACKEND, digest
from ...preprocessing.pipeline import LABEL, TARGETS
from ...preprocessing.scaling import Standardizer
from ..lstm.evaluation import batched_predictions, metric_row
from ..lstm.train import write_json


def verify(output):
    output=Path(output).resolve()
    class SavedGRUTests(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.report=json.loads((output/'training_report.json').read_text(encoding='utf-8'))
            cls.metrics=pd.read_csv(output/'test_metrics.csv')
            cls.model=keras.models.load_model(output/'gru_best.keras',compile=False)
            cls.saved={}
            for node in EXPECTED['test']:
                with np.load(output/f'test_predictions_{node}.npz',allow_pickle=False) as z:
                    cls.saved[node]={k:z[k] for k in z.files}

        def test_full_fresh_process_prediction_and_inverse_replay(self):
            scaler=Standardizer.from_dict(json.loads((output/'scalers_frozen.json').read_text(encoding='utf-8'))['target'])
            errors={}
            for node in EXPECTED['test']:
                x,_,_,_=load_node('test',node)
                prediction=batched_predictions(self.model,x,16)
                saved=self.saved[node]
                np.testing.assert_allclose(prediction,saved['predictions_scaled'],rtol=0,atol=1e-6)
                physical=scaler.inverse_transform(prediction,TARGETS)
                np.testing.assert_allclose(physical,saved['predictions_original_units'],rtol=0,atol=1e-5)
                self.assertEqual(prediction.shape,(811,168,3))
                errors[node]=dict(samples=len(x),scaled_max_abs_error=float(np.max(np.abs(prediction-saved['predictions_scaled']))),original_units_max_abs_error=float(np.max(np.abs(physical-saved['predictions_original_units']))))
            write_json(output/'reload_verification.json',dict(evaluation_label=LABEL,**errors))

        def test_architecture_and_selection(self):
            self.assertEqual(self.model.forecaster.count_params(),9987)
            self.assertEqual([type(l).__name__ for l in self.model.forecaster.layers],['InputLayer','GRU','RepeatVector','GRU','TimeDistributed'])
            history=pd.read_csv(output/'training_history.csv')
            self.assertEqual(len(history),self.report['epochs_completed'])
            self.assertEqual(int(history.loc[history.val_loss.idxmin(),'epoch']),self.report['best_epoch'])
            self.assertEqual(self.report['status'],'complete')
            self.assertTrue(self.report['validation_only_model_selection'])
            self.assertTrue((output/'first_epoch.keras').is_file())
            with zipfile.ZipFile(output/'best_validation.keras') as z:
                with h5py.File(io.BytesIO(z.read('model.weights.h5')),'r') as weights:
                    updates=int(weights['optimizer/vars/0'][()])
            self.assertEqual(updates,self.report['best_epoch']*((11137+15)//16))

        def test_identical_masks_labels_origins_and_reference(self):
            for node in EXPECTED['test']:
                _,_,mask,origins=load_node('test',node)
                s=self.saved[node]
                np.testing.assert_array_equal(mask,s['target_valid_mask'])
                np.testing.assert_array_equal(origins,s['forecast_origin_unix_ns'])
                with np.load(LSTM_OUTPUT/f'test_predictions_{node}.npz',allow_pickle=False) as reference:
                    assert_comparable(s['actual_original_units'],s['persistence_original_units'],mask,origins,reference)

        def test_all_three_model_metrics_independently_reproduced(self):
            values={}
            for node in EXPECTED['test']:
                s=self.saved[node]
                with np.load(LSTM_OUTPUT/f'test_predictions_{node}.npz',allow_pickle=False) as lstm:
                    values[node]=dict(actual=s['actual_original_units'],mask=s['target_valid_mask'],GRU=s['predictions_original_units'],LSTM=lstm['predictions_original_units'],Persistence=s['persistence_original_units'])
            values['POOLED']={k:np.concatenate([values[n][k] for n in EXPECTED['test']]) for k in values['NODE_01']}
            self.assertEqual(len(self.metrics),81)
            for row in self.metrics.itertuples():
                v=values[row.node];j=TARGETS.index(row.target);h=row.window_hours
                expected=metric_row(v['actual'][:,:h,j],v[row.model][:,:h,j],v['mask'][:,:h,j])
                self.assertEqual(row.valid_observations,expected['valid_observations'])
                for key in ('MAE','RMSE','R2'):self.assertAlmostEqual(getattr(row,key),expected[key],places=9)

        def test_comparison_counts_and_synthetic_labels(self):
            comparison=pd.read_csv(output/'three_model_comparison.csv')
            self.assertEqual(len(comparison),27)
            for name in ('persistence','lstm','gru'):
                np.testing.assert_array_equal(comparison[f'valid_observations_{name}'],comparison.valid_observations_gru)
            self.assertTrue(comparison.evaluation_label.eq(LABEL).all())
            self.assertTrue(self.metrics.evaluation_label.eq(LABEL).all())

        def test_protected_inputs_models_and_results_unchanged(self):
            provenance=json.loads((output/'input_provenance.json').read_text(encoding='utf-8'))
            for name,expected in provenance['protected_sha256'].items():
                self.assertEqual(digest(BACKEND/name),expected,name)
            self.assertEqual(digest(output/'scalers_frozen.json'),digest(DATA/'scalers.json'))

    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SavedGRUTests))
    (output/'post_training_tests.txt').write_text(LABEL+'\n'+stream.getvalue(),encoding='utf-8')
    write_json(output/'post_training_tests.json',dict(evaluation_label=LABEL,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped)))
    print(stream.getvalue(),flush=True)
    if result.wasSuccessful():
        from .reporting import write_reports
        write_reports(output)
    return result.wasSuccessful()


def main():
    parser=argparse.ArgumentParser(description=LABEL)
    parser.add_argument('--experiment',type=Path,required=True)
    args=parser.parse_args()
    tf.config.set_visible_devices([], 'GPU')
    tf.config.threading.set_intra_op_parallelism_threads(6)
    tf.config.threading.set_inter_op_parallelism_threads(1)
    raise SystemExit(0 if verify(args.experiment) else 1)


if __name__=='__main__':
    main()
