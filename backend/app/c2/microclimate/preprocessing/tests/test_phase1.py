"""Standard-library unittest tests; no pytest dependency."""
import unittest
import numpy as np
import pandas as pd
from ..pipeline import Config, TARGETS, load, partitions, persistence, quality_valid, scores, validate, windows
from ..run_phase1 import SOURCE, OUTPUT, digest


class Phase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load(SOURCE)

    def fixture(self,n=50):
        d=self.data[self.data.node_id.eq("NODE_01")].iloc[:n].copy().reset_index(drop=True)
        d["record_status"]="OK"; d["is_anomaly"]=False; d["is_imputed"]=False; d["imputed_fields"]=""
        for j,c in enumerate(TARGETS):
            d[c]=np.arange(n,dtype=float)+j
        return d

    def test_actual_schema_and_hourly_nodes(self):
        self.assertEqual(len(self.data),17520)
        self.assertEqual(self.data.node_id.nunique(),2)
        self.assertEqual(int(self.data.is_anomaly.sum()),64)
        self.assertEqual(int(self.data.is_imputed.sum()),234)

    def test_schema_missing_extra_duplicate(self):
        for d in [self.data.drop(columns="vpd_kpa"), self.data.assign(extra=1),
                  pd.concat([self.data,self.data[["vpd_kpa"]]],axis=1)]:
            with self.assertRaises(ValueError): validate(d)

    def test_required_missing_nonfinite_and_boolean(self):
        for c,v in [("air_temperature_c",np.nan),("quality_score",np.inf),("is_anomaly","false")]:
            d=self.data.copy(); d[c]=d[c].astype(object);d.loc[0,c]=v
            with self.assertRaises((ValueError,TypeError)): validate(d)

    def test_duplicates_and_gap_rejected(self):
        for d in [pd.concat([self.data,self.data.iloc[:1]]),self.data.drop(index=4)]:
            with self.assertRaises(ValueError): validate(d)

    def test_timestamp_timezone_and_alignment(self):
        for t in ["2025-01-01 00:00:00","2025-01-01T00:30:00+05:30","invalid"]:
            d=self.data.copy(); d.timestamp=d.timestamp.astype(object);d.loc[0,"timestamp"]=t
            with self.assertRaises(ValueError): validate(d)

    def test_flags_status_origin_ranges(self):
        for c,v in [("record_status","OTHER"),("data_origin","real"),("quality_score",2),
                    ("relative_humidity_pct",101),("light_lux",-1),("imputed_fields","unknown")]:
            d=self.data.copy();d.loc[0,c]=v
            with self.assertRaises(ValueError): validate(d)

    def test_ordering_preserves_nodes(self):
        sorted_data=validate(self.data.sample(frac=1,random_state=42))
        pd.testing.assert_frame_equal(sorted_data,self.data)

    def test_quality_policy(self):
        d=self.fixture(5)
        d.loc[0,"record_status"]="WARN"
        d.loc[1,"record_status"]="INVALID"
        d.loc[2,"is_anomaly"]=True
        d.loc[3,"is_imputed"]=True
        self.assertEqual(quality_valid(d).tolist(),[True,False,False,False,True])

    def test_shapes_alignment_and_persistence(self):
        d=self.fixture();c=Config(4,3)
        x,y,origins,count=windows(d,c)
        self.assertEqual(x.shape,(44,4,3));self.assertEqual(y.shape,(44,3,3));self.assertEqual(count,44)
        np.testing.assert_array_equal(x[0],d.loc[:3,TARGETS].to_numpy())
        np.testing.assert_array_equal(y[0],d.loc[4:6,TARGETS].to_numpy())
        self.assertEqual(origins[0],d.timestamp.iloc[3])
        self.assertEqual(origins[-1]+pd.Timedelta(hours=3),d.timestamp.iloc[-1])
        p=persistence(x,3)
        np.testing.assert_array_equal(p[0],np.tile(x[0,-1],(3,1)))

    def test_future_observations_cannot_change_history(self):
        d=self.fixture();c=Config(4,3)
        first=windows(d,c)[0][0].copy()
        d.loc[4:,list(TARGETS)]+=10000
        np.testing.assert_array_equal(windows(d,c)[0][0],first)

    def test_forward_fill_only_from_past(self):
        d=self.fixture();c=Config(4,3)
        d.loc[3,"record_status"]="INVALID"
        x,y,_,_=windows(d,c)
        np.testing.assert_array_equal(x[0,-1],d.loc[2,list(TARGETS)].to_numpy(dtype=float))
        np.testing.assert_array_equal(y[0],d.loc[4:6,TARGETS].to_numpy())

    def test_no_backfill_of_leading_bad_history(self):
        d=self.fixture();d.loc[0,"record_status"]="INVALID"
        _,_,origins,_=windows(d,Config(4,3))
        self.assertEqual(origins[0],d.timestamp.iloc[4])

    def test_flagged_target_windows_excluded(self):
        for flag in ["is_anomaly","is_imputed"]:
            d=self.fixture();d.loc[8,flag]=True
            _,_,origins,_=windows(d,Config(4,3))
            for origin in origins:
                self.assertFalse(origin < d.timestamp.iloc[8] <= origin+pd.Timedelta(hours=3))

    def test_split_before_windows_no_cross_boundary(self):
        d=self.fixture(50);c=Config(4,3,.5,.25)
        bounds=partitions(d,c)
        labels=[]
        for a,b in bounds.values():
            part=d[d.timestamp.between(a,b)]
            _,_,origins,_=windows(part,c)
            for t in origins:
                self.assertGreaterEqual(t-pd.Timedelta(hours=3),a)
                self.assertLessEqual(t+pd.Timedelta(hours=3),b)
                labels.append(set(pd.date_range(t+pd.Timedelta(hours=1),periods=3,freq="h")))
        self.assertLess(bounds["train"][1],bounds["validation"][0])
        self.assertLess(bounds["validation"][1],bounds["test"][0])
        for i,(a,b) in enumerate(bounds.values()):
            others=[(x,z) for k,(x,z) in enumerate(bounds.values()) if k!=i]
            for t in d[d.timestamp.between(a,b)].timestamp:
                self.assertTrue(all(not x<=t<=z for x,z in others))

    def test_no_nodes_mixed(self):
        with self.assertRaises(ValueError): windows(self.data,Config())

    def test_metrics_known_values_and_cumulative_horizons(self):
        y=np.zeros((2,168,3));p=np.ones_like(y)*2
        p[:,24:,:]=4
        rows,leads=scores(y,p)
        first=[r for r in rows if r["target"]==TARGETS[0]]
        self.assertEqual(first[0]["MAE"],2);self.assertEqual(first[0]["RMSE"],2)
        self.assertEqual(first[1]["MAE"],(24*2+48*4)/72)
        self.assertAlmostEqual(first[1]["RMSE"],np.sqrt((24*4+48*16)/72))
        self.assertEqual(first[2]["forecast_values"],336)
        self.assertEqual(len(leads),504);self.assertEqual(leads[24]["MAE"],4)

    def test_empty_windows_explicit_no_score(self):
        x,y,origins,candidates=windows(self.fixture(5),Config(4,3))
        self.assertEqual(x.shape,(0,4,3));self.assertEqual(y.shape,(0,3,3));self.assertEqual(candidates,0)
        rows,_=scores(np.empty((0,168,3)),np.empty((0,168,3)))
        self.assertTrue(all(r["MAE"] is None and r["samples"]==0 for r in rows))

    def test_invalid_config_and_evaluation(self):
        for kwargs in [{"lookback":0},{"stride":0},{"horizon":1.5},{"train_fraction":.9,"validation_fraction":.2}]:
            with self.assertRaises(ValueError): Config(**kwargs)
        with self.assertRaises(ValueError): scores(np.zeros((1,168,3)),np.zeros((1,24,3)))
        with self.assertRaises(ValueError): persistence(np.full((1,336,3),np.nan))

    def test_real_split_windows_and_all_target_timestamps(self):
        c=Config();bounds=partitions(self.data,c)
        expected={('train','NODE_01'):337,('train','NODE_02'):519,
                  ('validation','NODE_01'):0,('validation','NODE_02'):347,
                  ('test','NODE_01'):87,('test','NODE_02'):0}
        for split,(a,b) in bounds.items():
            for node,g in self.data.groupby('node_id'):
                part=g[g.timestamp.between(a,b)].reset_index(drop=True)
                x,y,origins,_=windows(part,c)
                self.assertEqual(len(y),expected[(split,node)])
                for i,t in enumerate(origins):
                    k=part.index[part.timestamp.eq(t)][0]
                    self.assertTrue(quality_valid(part.iloc[k+1:k+169]).all())
                    np.testing.assert_array_equal(y[i],part.iloc[k+1:k+169].loc[:,TARGETS].to_numpy())
                    self.assertGreaterEqual(t-pd.Timedelta(hours=335),a)
                    self.assertLessEqual(t+pd.Timedelta(hours=168),b)

    def test_executed_artifacts_reproduce_metrics_and_source_hash(self):
        import json
        if not (OUTPUT/'validation_report.json').exists():
            self.skipTest('Run experiment first for saved-artifact integration check')
        report=json.loads((OUTPUT/'validation_report.json').read_text(encoding='utf-8'))
        self.assertEqual(digest(SOURCE),report['source_sha256'])
        metrics=pd.read_csv(OUTPUT/'persistence_metrics.csv')
        for sample in report['samples']:
            with np.load(OUTPUT/sample['window_artifact'],allow_pickle=False) as data:
                x,y=data['X'],data['y']
                self.assertEqual(list(x.shape),sample['input_shape'])
                self.assertEqual(list(y.shape),sample['output_shape'])
                selected=metrics[metrics.split.eq(sample['split']) & metrics.node.eq(sample['node'])]
                for j,target in enumerate(TARGETS):
                    for h in (24,72,168):
                        row=selected[selected.target.eq(target)&selected.window_hours.eq(h)].iloc[0]
                        self.assertEqual(int(row.samples),len(y))
                        if len(y):
                            error=x[:,-1,j,None]-y[:,:h,j]
                            self.assertAlmostEqual(row.MAE,np.abs(error).mean(),places=10)
                            self.assertAlmostEqual(row.RMSE,np.sqrt((error**2).mean()),places=10)
                        else:
                            self.assertTrue(pd.isna(row.MAE) and pd.isna(row.RMSE))


if __name__=="__main__":
    unittest.main(verbosity=2)
