import sys
import unittest
from datetime import timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'practice' / 'iot_replay'))
from forecast import forecast_from_hourly
from replay import generate_readings
from hourly import aggregate_complete_hours
from schema import parse_aware_datetime

class ForecastIssueTimeTests(unittest.TestCase):
    def setUp(self):
        self.hourly = aggregate_complete_hours(generate_readings(hours=60))
        self.last_end = self.hourly[-1]['hour_end']

    def test_targets_are_strictly_after_issue_with_missing_recent_hour(self):
        issued = self.last_end + timedelta(hours=1, minutes=15)
        result = forecast_from_hourly(self.hourly, 'practice_plot_01', issued)
        self.assertEqual(result['status'], 'provisional')
        steps = [parse_aware_datetime(x['target_end']) for x in result['forecast']]
        self.assertEqual(len(steps), 24)
        self.assertTrue(all(x > issued for x in steps))
        self.assertEqual(steps[0], issued.replace(minute=0) + timedelta(hours=1))
        self.assertEqual(steps[-1]-steps[0], timedelta(hours=23))

    def test_exact_hour_issue_and_no_future_data_leakage(self):
        early = self.hourly[47]['hour_end']
        result = forecast_from_hourly(self.hourly, 'practice_plot_01', early)
        self.assertEqual(result['status'], 'provisional')
        self.assertEqual(parse_aware_datetime(result['forecast'][0]['target_end']), early + timedelta(hours=1))
        self.assertEqual(result['input_end'], early.isoformat())

    def test_bad_max_age_rejected(self):
        for invalid in (-1, float('nan'), '2'):
            with self.assertRaises(ValueError):
                forecast_from_hourly(self.hourly, 'practice_plot_01', self.last_end, max_age_hours=invalid)

if __name__=='__main__': unittest.main()
