"""Post-training saved-model, evaluation and preservation integration checks."""
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

from . import model as lstm_model
from ...preprocessing.pipeline import LABEL,TARGETS
from ...common.paths import BACKEND,digest
from .evaluation import metric_row
from ...common.paths import SCALED_OUTPUT as DATA


def verify(output, evidence_dir=None):
    output=Path(output).resolve()

    class SavedLSTMTests(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.report=json.loads((output/'training_report.json').read_text(encoding='utf-8'))
            cls.metrics=pd.read_csv(output/'test_metrics.csv')
            cls.model=keras.models.load_model(output/'lstm_best.keras',compile=False)

        def test_frozen_reload_inference_consistency(self):
            self.assertEqual(self.model.forecaster.count_params(),13027)
            with np.load(DATA/'windows_test_NODE_01.npz',allow_pickle=False) as z:
                actual=self.model(z['X'][:2],training=False).numpy()
            with np.load(output/'test_predictions_NODE_01.npz',allow_pickle=False) as z:
                np.testing.assert_allclose(actual,z['predictions_scaled'][:2],rtol=0,atol=1e-6)
            self.assertEqual(actual.shape,(2,168,3));self.assertTrue(np.isfinite(actual).all())

        def test_best_epoch_and_completed_training(self):
            history=pd.read_csv(output/'training_history.csv')
            self.assertEqual(len(history),self.report['epochs_completed'])
            self.assertEqual(int(history.loc[history.val_loss.idxmin(),'epoch']),self.report['best_epoch'])
            self.assertTrue((history.seconds>0).all())
            self.assertEqual(self.report['status'],'complete')
            self.assertTrue((output/'first_epoch.keras').is_file())
            self.assertTrue((output/'best_validation.keras').is_file())
            with zipfile.ZipFile(output/'best_validation.keras') as z:
                with h5py.File(io.BytesIO(z.read('model.weights.h5')),'r') as h:
                    updates=int(h['optimizer/vars/0'][()])
            self.assertEqual(updates,self.report['best_epoch']*((11137+15)//16))

        def test_identical_test_masks_and_temporal_alignment(self):
            for node in ('NODE_01','NODE_02'):
                with np.load(DATA/f'windows_test_{node}.npz',allow_pickle=False) as original,np.load(output/f'test_predictions_{node}.npz',allow_pickle=False) as predicted:
                    np.testing.assert_array_equal(original['target_valid_mask'],predicted['target_valid_mask'])
                    np.testing.assert_array_equal(original['forecast_origin_unix_ns'],predicted['forecast_origin_unix_ns'])
                    self.assertEqual(predicted['predictions_scaled'].shape,(811,168,3))
                    self.assertTrue(np.isfinite(predicted['predictions_original_units']).all())

        def test_metrics_and_pooled_denominators_independently_reproduced(self):
            loaded={}
            for node in ('NODE_01','NODE_02'):
                with np.load(output/f'test_predictions_{node}.npz',allow_pickle=False) as z:
                    loaded[node]={k:z[k] for k in ('actual_original_units','predictions_original_units','persistence_original_units','target_valid_mask')}
            loaded['POOLED']={k:np.concatenate([loaded[n][k] for n in ('NODE_01','NODE_02')]) for k in loaded['NODE_01']}
            for row in self.metrics.itertuples():
                v=loaded[row.node];j=TARGETS.index(row.target);h=row.window_hours
                p=v['predictions_original_units' if row.model=='LSTM' else 'persistence_original_units']
                expected=metric_row(v['actual_original_units'][:,:h,j],p[:,:h,j],v['target_valid_mask'][:,:h,j])
                self.assertEqual(row.valid_observations,expected['valid_observations'])
                for key in ('MAE','RMSE','R2'):
                    self.assertAlmostEqual(getattr(row,key),expected[key],places=9)

        def test_upstream_files_remain_unchanged(self):
            provenance=json.loads((output/'input_provenance.json').read_text(encoding='utf-8'))
            for name,expected in provenance['protected_sha256'].items():
                self.assertEqual(digest(BACKEND/name),expected,name)

    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SavedLSTMTests))
    evidence=output if evidence_dir is None else Path(evidence_dir).resolve()
    if evidence_dir is not None:
        if evidence == output or evidence.is_relative_to(output):
            raise ValueError('External evidence directory must be outside the experiment')
        evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'post_training_tests.txt').write_text(LABEL+'\n\n'+stream.getvalue(),encoding='utf-8')
    record=dict(evaluation_label=LABEL,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))
    (evidence/'post_training_tests.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(stream.getvalue())
    if result.wasSuccessful() and evidence_dir is None:
        from .reporting import write_reports
        write_reports(output)
    return result.wasSuccessful()


def main():
    p=argparse.ArgumentParser(description=LABEL);p.add_argument('--experiment',type=Path,required=True)
    p.add_argument('--evidence-dir',type=Path,help='Write verification logs externally and do not refresh experiment reports')
    args=p.parse_args()
    raise SystemExit(0 if verify(args.experiment,args.evidence_dir) else 1)


if __name__ == "__main__":
    main()
