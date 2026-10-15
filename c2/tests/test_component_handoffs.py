"""Regression tests for proposal-aligned C2 handoff helpers."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "handoffs"))
from input_checks import validate_c2_observation
from harvest_labels import next_week_fresh_yield
from downstream_contracts import validate_prediction


class InputTests(unittest.TestCase):
    def sample(self):
        return dict(plot_id="plot-01", timestamp="2026-01-01T05:30:00+05:30",
                    source="synthetic_practice", quality_flag="measured_valid",
                    calibration_version="practice-v1", soil_moisture=0.31,
                    soil_moisture_unit="m3_per_m3", air_temperature_c=28,
                    relative_humidity_pct=78)

    def test_canonical_utc_and_units(self):
        x = validate_c2_observation(self.sample())
        self.assertEqual(x["timestamp"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(x["soil_moisture_unit"], "m3_per_m3")

    def test_reject_unknown_unit_and_invalid_quality(self):
        with self.assertRaises(ValueError):
            validate_c2_observation({**self.sample(), "soil_moisture_unit": "raw_adc"})
        with self.assertRaises(ValueError):
            validate_c2_observation({**self.sample(), "quality_flag": "imputed"})
        with self.assertRaises(ValueError):
            validate_c2_observation({**self.sample(), "timestamp": "2026-01-01T00:00:00"})


class YieldTests(unittest.TestCase):
    def test_measured_next_week_mass_and_isolation(self):
        rows = [dict(plot_id="p",cycle_id="c",harvested_at="2026-01-03T00:00:00Z",
                     fresh_mass_kg=1.2,event_id="e1",measurement_type="measured_fresh_mass"),
                dict(plot_id="other",cycle_id="c",harvested_at="2026-01-03T00:00:00Z",
                     fresh_mass_kg=10,event_id="e2",measurement_type="measured_fresh_mass")]
        value = next_week_fresh_yield("p","c","2026-01-01T00:00:00Z",rows,"2026-01-08T00:00:00Z")
        self.assertEqual(value["status"], "available")
        self.assertAlmostEqual(value["fresh_yield_kg"], 1.2)
        self.assertEqual(value["harvest_event_count"], 1)

    def test_incomplete_coverage_not_zero_yield(self):
        value = next_week_fresh_yield("p","c","2026-01-01T00:00:00Z",[], "2026-01-06T00:00:00Z")
        self.assertEqual(value["status"], "unavailable")
        self.assertIsNone(value["fresh_yield_kg"])

    def test_duplicate_event_rejected(self):
        row=dict(plot_id="p",cycle_id="c",harvested_at="2026-01-03T00:00:00Z",
                 fresh_mass_kg=1,event_id="same",measurement_type="measured_fresh_mass")
        with self.assertRaises(ValueError):
            next_week_fresh_yield("p","c","2026-01-01T00:00:00Z",[row,row],"2026-01-08T00:00:00Z")


class DownstreamTests(unittest.TestCase):
    def base(self):
        return dict(prediction_id="test-1",plot_id="p",issued_at="2026-01-01T00:00:00Z",
                    target_start="2026-01-01T00:00:00Z",target_end="2026-01-02T00:00:00Z",
                    variable="soil_moisture",unit="m3_per_m3",median=0.3,lower=None,upper=None,
                    interval_level=None,model_version="practice-only",data_version="v1",
                    source="synthetic_practice",status="provisional")

    def test_valid_c3_and_c4(self):
        self.assertEqual(validate_prediction(self.base(),"c3")["status"],"provisional")
        y={**self.base(), "variable":"fresh_yield_kg_next_7_days","unit":"kg_per_plot","median":1.2}
        self.assertEqual(validate_prediction(y,"c4")["median"],1.2)

    def test_reject_wrong_consumer_and_uncertainty(self):
        with self.assertRaises(ValueError):
            validate_prediction(self.base(),"c4")
        with self.assertRaises(ValueError):
            validate_prediction({**self.base(),"lower":0.4,"upper":0.2,"interval_level":0.9},"c3")
        with self.assertRaises(ValueError):
            validate_prediction({**self.base(),"status":"unavailable"},"c3")


if __name__ == "__main__":
    unittest.main()
