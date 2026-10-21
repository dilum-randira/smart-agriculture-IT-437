"""Scaling unit/integration tests; original experiments are read-only."""
import json
import unittest

import numpy as np
import pandas as pd

from ..pipeline import Config, LABEL, TARGETS, load, quality_valid, masked_regression_loss
from ..run_phase1 import SOURCE
from ..run_phase1_masked import OUTPUT as MASKED
from ..run_phase1_scaled import OUTPUT, INVERSE_ATOL, METRIC_ATOL, protected_inventory
from ..scaling import (Standardizer, fit_standardizer, fit_training_scalers,
                      training_fit_observations)


class ScalingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = protected_inventory()
        cls.data = load(SOURCE)
        cls.previous = json.loads((MASKED/"validation_report.json").read_text(encoding="utf-8"))
        cls.report = json.loads((OUTPUT/"validation_report.json").read_text(encoding="utf-8"))
        cls.origins = {}
        for sample in cls.previous["samples"]:
            if sample["split"] == "train":
                with np.load(MASKED/sample["window_artifact"],allow_pickle=False) as z:
                    cls.origins[sample["node"]] = z["forecast_origin_unix_ns"].copy()
        train = cls.previous["splits"]["train"]
        cls.start, cls.end = pd.Timestamp(train["start"]), pd.Timestamp(train["end"])
        cls.scalers, cls.pools = fit_training_scalers(cls.data, cls.start, cls.end, cls.origins, Config())

    @classmethod
    def tearDownClass(cls):
        if protected_inventory() != cls.before:
            raise AssertionError("Protected source/unscaled artifacts changed during tests")

    def fit(self, data=None, origins=None):
        return fit_training_scalers(self.data if data is None else data, self.start, self.end,
                                    self.origins if origins is None else origins, Config())[0]

    def test_population_statistics_match_standard_scaler(self):
        from sklearn.preprocessing import StandardScaler
        for role, pool in self.pools.items():
            reference = StandardScaler().fit(pool.loc[:,TARGETS])
            scaler = self.scalers[role]
            np.testing.assert_allclose(scaler.mean, reference.mean_, rtol=0, atol=1e-10)
            np.testing.assert_allclose(scaler.variance, reference.var_, rtol=0, atol=1e-10)
            np.testing.assert_allclose(scaler.scale, reference.scale_, rtol=0, atol=1e-10)

    def test_validation_and_test_changes_do_not_affect_fit(self):
        altered = self.data.copy()
        heldout = altered.timestamp > self.end
        altered.loc[heldout,list(TARGETS)] = np.nan
        altered.loc[heldout,"is_anomaly"] = True
        changed = self.fit(altered)
        for role in self.scalers:
            self.assertEqual(changed[role].to_dict(), self.scalers[role].to_dict())

    def test_invalid_anomaly_imputed_training_values_cannot_affect_fit(self):
        altered = self.data.copy()
        excluded = ~quality_valid(altered)
        altered.loc[excluded,list(TARGETS)] = np.nan
        changed = self.fit(altered)
        for role in self.scalers:
            self.assertEqual(changed[role].to_dict(), self.scalers[role].to_dict())

    def test_unique_observations_not_overlap_weighted(self):
        duplicated = {node:np.repeat(values,3) for node,values in self.origins.items()}
        changed = self.fit(origins=duplicated)
        for role, pool in self.pools.items():
            self.assertFalse(pool.duplicated(["node_id","timestamp"]).any())
            self.assertTrue(pool.timestamp.between(self.start,self.end).all())
            self.assertEqual(changed[role].to_dict(),self.scalers[role].to_dict())
            self.assertEqual(self.scalers[role].counts,(len(pool),)*3)

    def test_fit_pools_only_source_genuine_observations(self):
        for pool in self.pools.values():
            joined=pool.merge(self.data,on=["node_id","timestamp"],validate="one_to_one",suffixes=("_fit","_raw"))
            self.assertTrue(quality_valid(joined).all())
            for feature in TARGETS:
                np.testing.assert_array_equal(joined[feature+"_fit"],joined[feature+"_raw"])

    def test_outside_training_window_or_duplicate_source_rejected(self):
        origins={k:v.copy() for k,v in self.origins.items()}
        origins['NODE_01']=np.append(origins['NODE_01'],pd.Timestamp('2025-11-10',tz='Asia/Colombo').value)
        with self.assertRaises(ValueError): self.fit(origins=origins)
        with self.assertRaises(ValueError): self.fit(pd.concat([self.data,self.data.iloc[:1]]))

    def test_feature_order_enforced(self):
        x=np.zeros((2,336,3))
        for role, scaler in self.scalers.items():
            with self.assertRaises(ValueError): scaler.transform(x,TARGETS[::-1])
            with self.assertRaises(ValueError): scaler.inverse_transform(x,TARGETS[::-1])
            with self.assertRaises(ValueError): scaler.transform_targets(x,np.ones_like(x,dtype=bool),TARGETS[::-1])
        with self.assertRaises(ValueError): fit_standardizer(np.zeros((5,3)),np.ones((5,3),bool),TARGETS[::-1])

    def test_serialized_parameters_round_trip(self):
        saved=json.loads((OUTPUT/'scalers.json').read_text(encoding='utf-8'))
        for role in self.scalers:
            loaded=Standardizer.from_dict(saved[role])
            self.assertEqual(loaded,self.scalers[role])
            np.testing.assert_array_equal(loaded.transform(np.ones((1,3)),TARGETS),self.scalers[role].transform(np.ones((1,3)),TARGETS))

    def test_zero_and_numerically_constant_variance(self):
        for values in [np.full((10,3),7.0),np.full((1,3),7.0),np.full((10,3),1e15)+np.arange(10)[:,None]*.125]:
            scaler=fit_standardizer(values,np.ones_like(values,bool))
            self.assertEqual(scaler.scale,(1.0,1.0,1.0))
            scaled=scaler.transform(values,TARGETS)
            self.assertTrue(np.isfinite(scaled).all())
            np.testing.assert_allclose(scaler.inverse_transform(scaled,TARGETS),values,rtol=0,atol=INVERSE_ATOL)

    def test_empty_eligible_feature_rejected(self):
        values=np.zeros((5,3));mask=np.ones_like(values,bool);mask[:,1]=False
        with self.assertRaises(ValueError): fit_standardizer(values,mask)

    def test_selected_fitting_ignores_untrusted_nonfinite_values(self):
        v=np.array([[1.,2.,3.],[3.,4.,5.],[np.inf,np.nan,-np.inf]])
        mask=np.array([[1,1,1],[1,1,1],[0,0,0]],dtype=bool)
        scaler=fit_standardizer(v,mask)
        self.assertEqual(scaler.mean,(2.,3.,4.))
        self.assertEqual(scaler.std,(1.,1.,1.))

    def test_target_placeholder_and_loss_are_mask_safe(self):
        scaler=self.scalers['target']
        y=np.array([[[50.,28.,80.],[np.nan,np.inf,-np.inf]]])
        mask=np.array([[[1,1,1],[0,0,0]]],dtype=bool)
        result=scaler.transform_targets(y,mask,TARGETS)
        self.assertEqual(result.dtype,np.float32)
        self.assertTrue(np.isfinite(result).all());self.assertTrue((result[~mask]==0).all())
        restored=scaler.inverse_targets(result,mask,TARGETS)
        self.assertTrue(np.isnan(restored[~mask]).all())
        prediction=result.astype(float)+.5
        prediction[~mask]=np.inf
        self.assertAlmostEqual(masked_regression_loss(result,prediction,mask),.25)
        self.assertAlmostEqual(masked_regression_loss(result,prediction,mask,'mae'),.5)

    def test_saved_shapes_dtypes_finiteness_masks_and_alignment(self):
        self.assertEqual(self.report['splits'],self.previous['splits'])
        for sample in self.previous['samples']:
            with np.load(MASKED/sample['window_artifact'],allow_pickle=False) as old, np.load(OUTPUT/sample['window_artifact'],allow_pickle=False) as new:
                for key in old.files:
                    if key not in {'X','y'}:
                        np.testing.assert_array_equal(new[key],old[key])
                for key in ('X','y'):
                    self.assertEqual(new[key].shape,old[key].shape)
                    self.assertEqual(new[key].dtype,np.float32)
                    self.assertTrue(np.isfinite(new[key]).all())
                self.assertTrue((new['y'][~new['target_valid_mask']]==0).all())
                self.assertEqual(str(new['evaluation_label']),LABEL)

    def test_saved_input_and_eligible_target_inverse_round_trips(self):
        for sample in self.previous['samples']:
            with np.load(MASKED/sample['window_artifact'],allow_pickle=False) as old, np.load(OUTPUT/sample['window_artifact'],allow_pickle=False) as new:
                restored_x=self.scalers['input'].inverse_transform(new['X'],TARGETS)
                np.testing.assert_allclose(restored_x,old['X'],rtol=0,atol=INVERSE_ATOL)
                mask=new['target_valid_mask']
                restored_y=self.scalers['target'].inverse_targets(new['y'],mask,TARGETS)
                np.testing.assert_allclose(restored_y[mask],old['y'][mask],rtol=0,atol=INVERSE_ATOL)
                self.assertTrue(np.isnan(restored_y[~mask]).all())

    def test_different_input_target_scalers_use_correct_inverse(self):
        self.assertNotEqual(self.scalers['input'].mean,self.scalers['target'].mean)
        raw=np.array([[[50.,28.,80.]]])
        x=self.scalers['input'].transform(raw,TARGETS)
        physical=self.scalers['input'].inverse_transform(x,TARGETS)
        y=self.scalers['target'].transform(physical,TARGETS)
        np.testing.assert_allclose(self.scalers['target'].inverse_transform(y,TARGETS),raw,rtol=0,atol=INVERSE_ATOL)

    def test_original_unit_metrics_and_denominators_reproduced(self):
        old=pd.read_csv(MASKED/'persistence_metrics.csv')
        new=pd.read_csv(OUTPUT/'original_unit_persistence_metrics.csv')
        old_lead=pd.read_csv(MASKED/'persistence_lead_time_metrics.csv')
        new_lead=pd.read_csv(OUTPUT/'original_unit_persistence_lead_time_metrics.csv')
        for a,b in [(old,new),(old_lead,new_lead)]:
            for key in ('split','node','target','valid_observations','possible_observations','samples'):
                np.testing.assert_array_equal(a[key],b[key])
            for metric in ('MAE','RMSE'):
                np.testing.assert_allclose(a[metric],b[metric],rtol=0,atol=METRIC_ATOL)

    def test_previous_artifacts_and_manifest_preserved(self):
        manifest=json.loads((OUTPUT/'preservation_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['protected_sha256'],protected_inventory())
        self.assertTrue(manifest['unchanged_after_execution'])
        self.assertEqual((OUTPUT/'sample_manifest.csv').read_bytes(),(MASKED/'sample_manifest.csv').read_bytes())


if __name__=='__main__':
    unittest.main(verbosity=2)
