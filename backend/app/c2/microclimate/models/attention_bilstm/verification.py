"""Fresh-process replay of primary forecasts, descriptive attention and metrics."""
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
from ..gru import model as gru_model  # Register c2>MaskedGRU for read-only baseline reload.
from .evaluation import REFERENCES,MODEL_NAME
from ...common.data import DATA,EXPECTED,load_node
from ...common.paths import BACKEND,digest
from ...preprocessing.pipeline import LABEL,TARGETS
from ...preprocessing.scaling import Standardizer
from ..lstm.evaluation import batched_predictions,metric_row
from ..lstm.train import write_json
from ..gru.evaluation import assert_comparable


def verify(output):
    output=Path(output).resolve()
    if not (output/'attention_bilstm_best.keras').is_file():
        raise ValueError('Expected completed Attention BiLSTM experiment; refusing writes elsewhere')
    class SavedAttentionTests(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.report=json.loads((output/'training_report.json').read_text(encoding='utf-8'))
            cls.metrics=pd.read_csv(output/'test_metrics.csv')
            cls.model=keras.models.load_model(output/'attention_bilstm_best.keras',compile=False)
            cls.saved={}
            for node in EXPECTED['test']:
                with np.load(output/f'test_predictions_{node}.npz',allow_pickle=False) as z:
                    cls.saved[node]={k:z[k] for k in z.files}

        def test_complete_fresh_process_forecast_replay(self):
            target=Standardizer.from_dict(json.loads((output/'scalers_frozen.json').read_text(encoding='utf-8'))['target'])
            evidence={}
            for node in EXPECTED['test']:
                x,_,_,_=load_node('test',node)
                p=batched_predictions(self.model,x,16);original=self.saved[node]
                np.testing.assert_allclose(p,original['predictions_scaled'],rtol=0,atol=1e-6)
                physical=target.inverse_transform(p,TARGETS)
                np.testing.assert_allclose(physical,original['predictions_original_units'],rtol=0,atol=1e-5)
                self.assertEqual(p.shape,(811,168,3));self.assertTrue(np.isfinite(p).all())
                evidence[node]=dict(samples=len(x),scaled_max_abs_error=float(np.max(np.abs(p-original['predictions_scaled']))),
                                    original_units_max_abs_error=float(np.max(np.abs(physical-original['predictions_original_units']))))
            write_json(output/'reload_verification.json',dict(evaluation_label=LABEL,**evidence))

        def test_descriptive_attention_replay_and_historical_alignment(self):
            for node in EXPECTED['test']:
                x,_,_,origins=load_node('test',node)
                with np.load(output/f'attention_{node}.npz',allow_pickle=False) as z:
                    weights=self.model.attention_weights(x[:1]).numpy()
                    self.assertEqual(weights.shape,(1,336));self.assertTrue(np.isfinite(weights).all())
                    self.assertTrue((weights>=0).all())
                    np.testing.assert_allclose(weights.sum(axis=1),1.,rtol=0,atol=1e-6)
                    np.testing.assert_allclose(weights,z['weights'],rtol=0,atol=1e-6)
                    np.testing.assert_array_equal(x[:1],z['historical_inputs_scaled'])
                    expected=origins[0]-np.arange(335,-1,-1,dtype=np.int64)*3600*10**9
                    np.testing.assert_array_equal(z['historical_timestamps_unix_ns'],expected)
                    self.assertTrue((z['historical_timestamps_unix_ns']<=origins[0]).all())
                    self.assertIn('not causal',str(z['interpretation']))
                    with np.load(DATA/f'windows_test_{node}.npz',allow_pickle=False) as source:
                        np.testing.assert_array_equal(z['history_valid_mask'],source['history_valid_mask'][:1])

        def test_exact_architecture_and_projection(self):
            self.assertEqual(self.model.forecaster.count_params(),30040)
            encoder=self.model.forecaster.get_layer('historical_bilstm')
            self.assertEqual(encoder.forward_layer.units,32);self.assertEqual(encoder.backward_layer.units,32)
            self.assertTrue(encoder.forward_layer.return_sequences)
            self.assertEqual(self.model.forecaster.get_layer('temporal_attention').count_params(),2112)
            self.assertEqual(self.model.forecaster.input_shape,(None,336,3))
            self.assertEqual(self.model.forecaster.output_shape,(None,168,3))

        def test_validation_only_selection_and_complete_epoch_evidence(self):
            history=pd.read_csv(output/'training_history.csv')
            self.assertEqual(len(history),self.report['epochs_completed'])
            self.assertEqual(int(history.loc[history.val_loss.idxmin(),'epoch']),self.report['best_epoch'])
            self.assertEqual(self.report['status'],'complete')
            self.assertTrue(self.report['validation_only_model_selection'])
            self.assertTrue((history.validation_valid_elements==805122).all())
            self.assertTrue((output/'first_epoch.keras').is_file())
            with zipfile.ZipFile(output/'best_validation.keras') as z:
                with h5py.File(io.BytesIO(z.read('model.weights.h5')),'r') as weights:
                    self.assertEqual(int(weights['optimizer/vars/0'][()]),self.report['best_epoch']*((11137+15)//16))

        def test_preserved_lstm_and_gru_reload_without_training(self):
            x,_,_,_=load_node('test','NODE_01')
            for name,path in REFERENCES.items():
                baseline=keras.models.load_model(path/('lstm_best.keras' if name=='LSTM' else 'gru_best.keras'),compile=False)
                with np.load(path/'test_predictions_NODE_01.npz',allow_pickle=False) as ref:
                    np.testing.assert_allclose(baseline(x[:2],training=False).numpy(),ref['predictions_scaled'][:2],rtol=0,atol=1e-6)

        def test_all_original_unit_metrics_and_counts_recomputed(self):
            cohorts={}
            for node in EXPECTED['test']:
                s=self.saved[node];cohorts[node]=dict(actual=s['actual_original_units'],mask=s['target_valid_mask'],
                                                      AttentionBiLSTM=s['predictions_original_units'],Persistence=s['persistence_original_units'])
                _,_,mask,origins=load_node('test',node)
                np.testing.assert_array_equal(mask,s['target_valid_mask']);np.testing.assert_array_equal(origins,s['forecast_origin_unix_ns'])
                for name,path in REFERENCES.items():
                    with np.load(path/f'test_predictions_{node}.npz',allow_pickle=False) as ref:
                        assert_comparable(s['actual_original_units'],s['persistence_original_units'],mask,origins,ref)
                        cohorts[node][name]=ref['predictions_original_units'].copy()
            cohorts['POOLED']={k:np.concatenate([cohorts[n][k] for n in EXPECTED['test']]) for k in cohorts['NODE_01']}
            self.assertEqual(len(self.metrics),108)
            for row in self.metrics.itertuples():
                c=cohorts[row.node];j=TARGETS.index(row.target);h=row.window_hours
                expected=metric_row(c['actual'][:,:h,j],c[row.model][:,:h,j],c['mask'][:,:h,j])
                self.assertEqual(row.valid_observations,expected['valid_observations'])
                for key in ('MAE','RMSE','R2'):self.assertAlmostEqual(getattr(row,key),expected[key],places=9)

        def test_four_model_winners_counts_and_labels(self):
            table=pd.read_csv(output/'four_model_comparison.csv');self.assertEqual(len(table),27)
            names=['Persistence','LSTM','GRU',MODEL_NAME]
            for n in names:np.testing.assert_array_equal(table[f'valid_observations_{n}'],table.valid_observations_Persistence)
            for row in table.itertuples():
                scores={name:getattr(row,f'RMSE_{name}') for name in names}
                best=min(scores.values())
                self.assertEqual(row.RMSE_winner,', '.join(n for n,v in scores.items() if np.isclose(v,best,rtol=0,atol=1e-12)))
            self.assertTrue(table.evaluation_label.eq(LABEL).all());self.assertTrue(self.metrics.evaluation_label.eq(LABEL).all())
            self.assertEqual(len(pd.read_csv(output/'test_lead_metrics.csv')),6048)

        def test_frozen_scalers_and_all_upstream_hashes(self):
            provenance=json.loads((output/'input_provenance.json').read_text(encoding='utf-8'))
            for name,expected in provenance['protected_sha256'].items():self.assertEqual(digest(BACKEND/name),expected,name)
            self.assertEqual(digest(output/'scalers_frozen.json'),digest(DATA/'scalers.json'))

    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SavedAttentionTests))
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


if __name__=='__main__':main()
