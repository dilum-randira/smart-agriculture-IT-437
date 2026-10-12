import sys
import unittest
from datetime import timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "iot_replay"))
from replay import generate_readings
from hourly import aggregate_complete_hours
from forecast import forecast_from_hourly


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.rows = aggregate_complete_hours(generate_readings(hours=50))
        self.issued_at = self.rows[-1]["hour_end"] + timedelta(minutes=5)

    def test_provisional_reference_only(self):
        got = forecast_from_hourly(self.rows, "practice_plot_01", self.issued_at)
        self.assertEqual(got["status"], "provisional")
        self.assertEqual(len(got["forecast"]), 24)
        self.assertIn("not_trained", got["model"])
        self.assertEqual(got["forecast"][0]["values"]["air_temperature_c"]["unit"], "degC")

    def test_no_history_and_short_history(self):
        self.assertEqual(forecast_from_hourly(self.rows, "other", self.issued_at)["status"], "unavailable")
        short = forecast_from_hourly(self.rows[:20], "practice_plot_01",
                                     self.rows[19]["hour_end"], max_age_hours=2)
        self.assertEqual(short["status"], "unavailable")

    def test_stale_observations(self):
        got = forecast_from_hourly(self.rows, "practice_plot_01",
                                   self.issued_at + timedelta(hours=4))
        self.assertEqual(got["status"], "stale")
        self.assertEqual(got["forecast"], [])

    def test_gap_disables_forecast(self):
        gapped = self.rows[:25] + self.rows[26:]
        got = forecast_from_hourly(gapped, "practice_plot_01", self.issued_at)
        self.assertEqual(got["status"], "unavailable")
        self.assertIn("gaps", got["reason"])

    def test_no_future_history_and_timezone_requirements(self):
        future = forecast_from_hourly(self.rows, "practice_plot_01",
                                      self.rows[20]["hour_end"], lookback_hours=48)
        self.assertEqual(future["status"], "unavailable")
        with self.assertRaises(ValueError):
            forecast_from_hourly(self.rows, "practice_plot_01",
                                 self.issued_at.replace(tzinfo=None))


if __name__ == "__main__":
    unittest.main()
