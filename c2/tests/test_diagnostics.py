import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'practice' / 'time_series'))
from diagnostics import cumulative_metrics, lead_time_metrics, validate_forecasts


class ForecastDiagnosticsTests(unittest.TestCase):
    def test_per_lead_and_cumulative_values(self):
        actual = np.array([[1., 2., 3.], [3., 4., 5.]])
        predicted = np.array([[0., 2., 5.], [3., 2., 4.]])
        lead = lead_time_metrics(actual, predicted)
        np.testing.assert_array_equal(lead['lead_hour'], [1, 2, 3])
        np.testing.assert_allclose(lead['mae'], [.5, 1., 1.5])
        self.assertAlmostEqual(cumulative_metrics(actual, predicted, (3,))[3]['MAE'], 1.)
        self.assertEqual(cumulative_metrics(actual, predicted, (3,))[3]['forecast_origins'], 2)

    def test_invalid_values_and_shapes_rejected(self):
        for actual, predicted in [(np.ones((2, 2)), np.ones((2, 3))),
                                  (np.array([[np.nan]]), np.array([[1.]])),
                                  (np.array([1.]), np.array([1.]))]:
            with self.assertRaises(ValueError):
                validate_forecasts(actual, predicted)
        with self.assertRaises(ValueError):
            cumulative_metrics(np.ones((2, 3)), np.ones((2, 3)), (4,))


if __name__ == '__main__':
    unittest.main()
