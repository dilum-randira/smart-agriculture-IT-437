"""Basic reproducibility and shape checks for the educational example."""

import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "practice" / "yield_regression.py"
spec = importlib.util.spec_from_file_location("yield_regression", MODULE)
yield_regression = importlib.util.module_from_spec(spec)
spec.loader.exec_module(yield_regression)


class YieldRegressionPracticeTests(unittest.TestCase):
    def test_synthetic_dataset_schema_and_reproducibility(self):
        first = yield_regression.make_practice_data()
        second = yield_regression.make_practice_data()
        self.assertEqual(first.shape, (300, 5))
        self.assertFalse(first.isna().any().any())
        self.assertTrue(first.equals(second))

    def test_forest_beats_mean_on_this_fixed_practice_data(self):
        results, prediction = yield_regression.run_experiment()
        self.assertLess(results["Random Forest"]["MAE"], results["Training Mean"]["MAE"])
        self.assertGreaterEqual(prediction, 0)


if __name__ == "__main__":
    unittest.main()
