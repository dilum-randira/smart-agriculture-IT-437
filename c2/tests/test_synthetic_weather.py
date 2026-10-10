"""Tests for synthetic weather generator used in educational practice."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "time_series"))
from synthetic_weather import make_synthetic_hourly_weather


class SyntheticWeatherTests(unittest.TestCase):
    def test_reproducible_schema(self):
        first = make_synthetic_hourly_weather(hours=96)
        second = make_synthetic_hourly_weather(hours=96)
        self.assertTrue(first.equals(second))
        self.assertEqual(first.shape, (96, 4))
        self.assertFalse(first.isna().any().any())
        self.assertTrue(first["timestamp"].is_monotonic_increasing)
        self.assertTrue(first["timestamp"].is_unique)

    def test_bounded_practice_percentages(self):
        data = make_synthetic_hourly_weather(hours=96)
        for field in ("relative_humidity_pct", "synthetic_soil_moisture_pct"):
            self.assertTrue(data[field].between(0, 100).all())

    def test_short_series_rejected(self):
        with self.assertRaises(ValueError):
            make_synthetic_hourly_weather(hours=24)


if __name__ == "__main__":
    unittest.main()
