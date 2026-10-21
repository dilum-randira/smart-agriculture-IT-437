"""Target-mask unit and saved-artifact integration tests (no model training)."""
import json
import unittest

import numpy as np
import pandas as pd

from ..pipeline import (Config, TARGETS, LABEL, load, quality_valid, partitions,
                       masked_windows, masked_scores, masked_regression_loss, windows)
from ..run_phase1 import SOURCE, digest
from ..run_phase1_masked import OUTPUT, protected_inventory, training_quality


class TargetMaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protected = protected_inventory()
        cls.data = load(SOURCE)

    @classmethod
    def tearDownClass(cls):
        if protected_inventory() != cls.protected:
            raise AssertionError("Original data/Phase 1 artifacts changed during tests")

    def fixture(self, n=60):
        d = self.data[self.data.node_id.eq("NODE_01")].iloc[:n].copy().reset_index(drop=True)
        d["record_status"] = "OK"
        d["is_anomaly"] = False
        d["is_imputed"] = False
        d["imputed_fields"] = ""
        for j, name in enumerate(TARGETS):
            d[name] = np.arange(n, dtype=float)+j
        return d

    def test_mask_shape_binary_and_temporal_alignment(self):
        d = self.fixture()
        d.loc[10, "record_status"] = "INVALID"
        x, y, mask, origins, candidates = masked_windows(d, Config(4,24))
        self.assertEqual(mask.shape, y.shape)
        self.assertEqual(mask.dtype, np.dtype(bool))
        self.assertEqual(set(np.unique(mask)), {False, True})
        self.assertEqual(candidates, 33)
        np.testing.assert_array_equal(x[0], d.loc[:3, TARGETS].to_numpy())
        np.testing.assert_array_equal(y[0], d.loc[4:27, TARGETS].to_numpy())
        self.assertFalse(mask[0,6].any())
        self.assertEqual(origins[0], d.timestamp.iloc[3])

    def test_all_untrusted_flags_excluded_and_clean_warn_retained(self):
        for column, value in [("record_status", "INVALID"), ("is_anomaly", True), ("is_imputed", True)]:
            d = self.fixture()
            d.loc[10, column] = value
            _, y, mask, _, _ = masked_windows(d, Config(4,24))
            self.assertFalse(mask[0,6].any())
            np.testing.assert_array_equal(y[0,6], d.loc[10, list(TARGETS)].to_numpy(dtype=float))
        d = self.fixture()
        d.loc[10, "record_status"] = "WARN"
        self.assertTrue(masked_windows(d, Config(4,24))[2][0,6].all())

    def test_quality_captured_before_history_filling(self):
        d = self.fixture()
        d.loc[10,"is_imputed"] = True
        d.loc[10,list(TARGETS)] = 999999
        x,y,mask,origins,_ = masked_windows(d,Config(4,24))
        self.assertFalse(mask[0,6].any())
        self.assertTrue((y[0,6] == 999999).all())  # Raw target is NOT interpolated.
        i = origins.index(d.timestamp.iloc[10])
        np.testing.assert_array_equal(x[i,-1],d.loc[9,list(TARGETS)].to_numpy(dtype=float))

    def test_95_percent_rule_and_no_empty_labels(self):
        d = self.fixture()
        d.loc[[10,11],"is_anomaly"] = True
        _,_,_,origins,_ = masked_windows(d,Config(4,24))
        self.assertNotIn(d.timestamp.iloc[3],origins)  # 22/24 < ceil(.95*24)=23.
        d["record_status"] = "INVALID"
        x,y,m,origins,_ = masked_windows(d,Config(4,24))
        self.assertEqual(x.shape,(0,4,3)); self.assertEqual(y.shape,(0,24,3))
        self.assertEqual(m.shape,(0,24,3)); self.assertEqual(origins,[])

    def test_known_metric_denominators_and_masked_loss(self):
        y = np.zeros((2,168,3))
        p = np.full_like(y,2)
        mask = np.ones_like(y,dtype=bool)
        p[0,0,0] = 4
        mask[1,0,0] = False
        y[1,0,0] = np.nan
        p[1,0,0] = np.inf
        rows,leads = masked_scores(y,p,mask)
        r = rows[0]
        self.assertEqual(r["valid_observations"],47)
        self.assertEqual(r["masked_observations"],1)
        self.assertEqual(r["contributing_samples"],2)
        self.assertAlmostEqual(r["MAE"],(4+46*2)/47)
        self.assertAlmostEqual(r["RMSE"],np.sqrt((16+46*4)/47))
        self.assertEqual(leads[0]["valid_observations"],1)
        self.assertEqual(leads[0]["MAE"],4)
        self.assertEqual(masked_regression_loss(y[:,:1,:1],p[:,:1,:1],mask[:,:1,:1]),16)
        self.assertEqual(masked_regression_loss(y[:,:1,:1],p[:,:1,:1],mask[:,:1,:1],"mae"),4)

    def test_prefix_horizons_are_cumulative(self):
        y=np.zeros((1,168,3));p=np.ones_like(y)
        p[:,24:72]=3; p[:,72:]=5
        rows,_=masked_scores(y,p,np.ones_like(y,dtype=bool))
        self.assertEqual(rows[0]["MAE"],1)
        self.assertEqual(rows[1]["MAE"],(24+48*3)/72)
        self.assertEqual(rows[2]["MAE"],(24+48*3+96*5)/168)

    def test_zero_denominators_and_empty_cohorts(self):
        for n in (0,2):
            y=np.zeros((n,168,3));m=np.zeros_like(y,dtype=bool)
            rows,leads=masked_scores(y,y,m)
            self.assertTrue(all(r["MAE"] is None and r["RMSE"] is None and r["valid_observations"]==0 for r in rows+leads))
            self.assertIsNone(masked_regression_loss(y,y,m))

    def test_zero_prefix_with_nonzero_later_labels(self):
        y=np.zeros((1,168,3));p=np.ones_like(y);m=np.ones_like(y,dtype=bool)
        m[:,:24]=False
        rows,_=masked_scores(y,p,m)
        self.assertIsNone(rows[0]["MAE"])
        self.assertEqual(rows[1]["valid_observations"],48)
        self.assertEqual(rows[1]["MAE"],1)

    def test_bad_mask_and_eligible_nonfinite_rejected(self):
        y=np.zeros((1,168,3))
        with self.assertRaises(ValueError): masked_scores(y,y,np.full_like(y,.5))
        with self.assertRaises(ValueError): masked_scores(y,y,np.ones((1,168,1),dtype=bool))
        y[0,0,0]=np.nan
        with self.assertRaises(ValueError): masked_scores(y,np.zeros_like(y),np.ones_like(y,dtype=bool))
        for fraction in (0,-1,1.1,np.nan):
            with self.assertRaises(ValueError): masked_windows(self.fixture(),Config(),fraction)

    def test_future_values_and_quality_never_enter_inputs(self):
        d=self.fixture(); c=Config(4,24)
        x,y,m,_,_=masked_windows(d,c)
        d.loc[4:,list(TARGETS)]+=100000
        d.loc[10,"is_imputed"]=True
        newer=masked_windows(d,c)
        np.testing.assert_array_equal(newer[0][0],x[0])
        self.assertFalse(newer[2][0,6].any())

    def test_no_backward_fill_or_node_mixing(self):
        d=self.fixture();d.loc[0,"is_anomaly"]=True
        _,_,_,origins,_=masked_windows(d,Config(4,24))
        self.assertEqual(origins[0],d.timestamp.iloc[4])
        with self.assertRaises(ValueError): masked_windows(self.data,Config())

    def test_frozen_literal_boundaries(self):
        b=partitions(self.data,Config())
        expected={"train":("2025-01-01T00:00:00+05:30","2025-09-13T11:00:00+05:30"),
                  "validation":("2025-09-13T12:00:00+05:30","2025-11-07T05:00:00+05:30"),
                  "test":("2025-11-07T06:00:00+05:30","2025-12-31T23:00:00+05:30")}
        self.assertEqual({s:(a.isoformat(),z.isoformat()) for s,(a,z) in b.items()},expected)

    def test_development_analysis_is_training_only(self):
        c=Config();b=partitions(self.data,c)
        before=training_quality(self.data,b,c)
        altered=self.data.copy()
        altered.loc[altered.timestamp>b['train'][1],'is_anomaly']=True
        self.assertEqual(before,training_quality(altered,b,c))
        self.assertEqual([n['meeting_coverage_rule'] for n in before['nodes']],[5629,5508])

    def test_complete_case_interface_preserved(self):
        d=self.fixture();d.loc[10,'is_imputed']=True;c=Config(4,24)
        old=windows(d,c);masked=masked_windows(d,c,1.0)
        np.testing.assert_array_equal(old[0],masked[0])
        np.testing.assert_array_equal(old[1],masked[1])
        self.assertEqual(old[2],masked[3]);self.assertTrue(masked[2].all())

    def test_source_and_original_artifacts_preserved(self):
        manifest=json.loads((OUTPUT/'preservation_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['protected_sha256'],protected_inventory())
        self.assertTrue(manifest['unchanged_after_execution'])

    def test_saved_arrays_masks_alignment_and_counts(self):
        report=json.loads((OUTPUT/'validation_report.json').read_text(encoding='utf-8'))
        expected={('train','NODE_01'):5629,('train','NODE_02'):5508,
                  ('validation','NODE_01'):811,('validation','NODE_02'):811,
                  ('test','NODE_01'):811,('test','NODE_02'):811}
        for sample in report['samples']:
            with np.load(OUTPUT/sample['window_artifact'],allow_pickle=False) as z:
                x,y,m=z['X'],z['y'],z['target_valid_mask']
                self.assertEqual(len(y),expected[(sample['split'],sample['node'])])
                self.assertEqual(m.shape,y.shape);self.assertEqual(m.dtype,np.dtype(bool))
                self.assertTrue((m.sum(axis=1)>=160).all())
                self.assertEqual(str(z['evaluation_label']),LABEL)
                g=self.data[self.data.node_id.eq(sample['node'])].reset_index(drop=True)
                origins=pd.to_datetime(z['forecast_origin_unix_ns'],utc=True).tz_convert('Asia/Colombo')
                positions=pd.DatetimeIndex(g.timestamp).get_indexer(origins)
                indices=positions[:,None]+1+np.arange(168)
                raw=g.loc[:,TARGETS].to_numpy()
                np.testing.assert_array_equal(y,raw[indices])
                expected_mask=np.repeat(quality_valid(g).to_numpy()[indices][...,None],3,axis=2)
                np.testing.assert_array_equal(m,expected_mask)
                start=pd.Timestamp(report['splits'][sample['split']]['start'])
                end=pd.Timestamp(report['splits'][sample['split']]['end'])
                self.assertTrue((origins-pd.Timedelta(hours=335)>=start).all())
                self.assertTrue((origins+pd.Timedelta(hours=168)<=end).all())
                self.assertEqual(m.sum(axis=(0,1)).tolist(),list(sample['valid_observations_per_target'].values()))

    def test_saved_metrics_independently_reproduced(self):
        metrics=pd.read_csv(OUTPUT/'persistence_metrics.csv')
        report=json.loads((OUTPUT/'validation_report.json').read_text(encoding='utf-8'))
        for sample in report['samples']:
            with np.load(OUTPUT/sample['window_artifact'],allow_pickle=False) as z:
                for row in metrics[metrics.split.eq(sample['split'])&metrics.node.eq(sample['node'])].itertuples():
                    j=TARGETS.index(row.target);h=row.window_hours
                    mask=z['target_valid_mask'][:,:h,j]
                    actual=z['y'][:,:h,j][mask]
                    pred=np.broadcast_to(z['X'][:,-1,j,None],mask.shape)[mask]
                    self.assertEqual(len(actual),row.valid_observations)
                    self.assertAlmostEqual(np.abs(pred-actual).mean(),row.MAE,places=10)
                    self.assertAlmostEqual(np.sqrt(np.square(pred-actual).mean()),row.RMSE,places=10)


if __name__=='__main__':
    unittest.main(verbosity=2)
