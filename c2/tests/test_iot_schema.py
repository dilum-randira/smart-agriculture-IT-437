import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "iot_replay"))
from schema import validate_reading


def sample():
    return {
        "plot_id": "practice_plot_01",
        "recorded_at": "2026-01-01T00:15:00+00:00",
        "soil_moisture_pct": 30,
        "air_temperature_c": 29.5,
        "relative_humidity_pct": 75,
        "rainfall_mm": 0.0,
        "source": "synthetic_practice",
        "quality_flag": "valid",
        "growth_stage": "Vegetative",
    }


class InputContractTests(unittest.TestCase):
    def test_valid_record_is_utc_aware(self):
        record = validate_reading(sample())
        self.assertEqual(record["recorded_at"].utcoffset().total_seconds(), 0)
        self.assertEqual(record["air_temperature_c"], 29.5)

    def test_timestamp_without_timezone_is_rejected(self):
        record = sample()
        record["recorded_at"] = "2026-01-01T00:15:00"
        with self.assertRaises(ValueError):
            validate_reading(record)

    def test_missing_and_out_of_range_rejected(self):
        reading = sample()
        del reading["rainfall_mm"]
        with self.assertRaises(ValueError):
            validate_reading(reading)
        reading = sample()
        reading["relative_humidity_pct"] = 110
        with self.assertRaises(ValueError):
            validate_reading(reading)
        reading = sample()
        reading["air_temperature_c"] = float("nan")
        with self.assertRaises(ValueError):
            validate_reading(reading)

    def test_non_synthetic_source_rejected(self):
        reading = sample()
        reading["source"] = "real_iot"
        with self.assertRaises(ValueError):
            validate_reading(reading)


if __name__ == "__main__":
    unittest.main()
