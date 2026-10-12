import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "iot_replay"))
from replay import generate_readings
from hourly import aggregate_complete_hours


class HourlyTests(unittest.TestCase):
    def test_hours_and_plot_isolation(self):
        a = list(generate_readings(hours=3, plot_id="a"))
        b = list(generate_readings(hours=2, plot_id="b"))
        hourly = aggregate_complete_hours(a + b)
        self.assertEqual(len(hourly), 5)
        self.assertEqual([r["plot_id"] for r in hourly], ["a", "a", "a", "b", "b"])
        self.assertTrue(all(r["record_count"] == 4 for r in hourly))

    def test_partial_or_invalid_hour_excluded(self):
        readings = list(generate_readings(hours=2))
        self.assertEqual(len(aggregate_complete_hours(readings[:-1])), 1)
        readings[0] = {**readings[0], "quality_flag": "invalid"}
        self.assertEqual(len(aggregate_complete_hours(readings)), 1)

    def test_duplicates_do_not_create_extra_readings(self):
        readings = list(generate_readings(hours=1))
        self.assertEqual(len(aggregate_complete_hours(readings + readings[:1])), 1)
        conflicting = {**readings[0], "air_temperature_c": 5.0}
        self.assertEqual(len(aggregate_complete_hours(readings + [conflicting])), 0)


if __name__ == "__main__":
    unittest.main()
