import json
import sys
import unittest
from pathlib import Path
from datetime import timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'practice'/'iot_replay'))
from hourly import aggregate_complete_hours
from replay import generate_readings
from forecast import forecast_from_hourly
from contracts import publishable_payload

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.rows=aggregate_complete_hours(generate_readings(hours=60))
        self.issued=self.rows[-1]['hour_end']+timedelta(minutes=10)
        self.base=forecast_from_hourly(self.rows,'practice_plot_01',self.issued)

    def test_versioned_output_has_72_hourly_variable_rows(self):
        result=publishable_payload(self.base)
        self.assertEqual(len(result['predictions']),72)
        self.assertEqual(result['status'],'provisional')
        self.assertTrue(all(p['lower'] is None and p['upper'] is None for p in result['predictions']))
        self.assertEqual(len({p['prediction_id'] for p in result['predictions']}),72)
        self.assertEqual(result, json.loads(json.dumps(result)))
        self.assertEqual(result,publishable_payload(self.base))

    def test_unavailable_and_stale_publish_no_predictions(self):
        for status in ('unavailable','stale'):
            result={**self.base,'status':status,'forecast':[], 'reason':'test'}
            self.assertEqual(publishable_payload(result)['predictions'],[])

    def test_reject_unlabelled_data_or_past_targets(self):
        with self.assertRaises(ValueError):
            publishable_payload({**self.base,'source':'real_iot'})
        early={**self.base,'forecast':[{**self.base['forecast'][0],'target_end':self.base['issued_at']}]}
        with self.assertRaises(ValueError):publishable_payload(early)

    def test_stage_as_of_issue_included_when_available(self):
        stage=[{'plot_id':'practice_plot_01','growth_stage':'Flowering',
                'observed_at':(self.issued-timedelta(hours=2)).isoformat(),
                'recorded_at':(self.issued-timedelta(hours=1)).isoformat()}]
        self.assertEqual(publishable_payload(self.base,stage_events=stage)['growth_stage']['growth_stage'],'Flowering')

if __name__=='__main__':unittest.main()
