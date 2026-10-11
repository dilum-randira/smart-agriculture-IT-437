import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'practice' / 'time_series'))
from seasonal_naive import seasonal_naive_forecast


class SeasonalNaiveTests(unittest.TestCase):
    def test_repeat_last_cycle_longer_than_cycle(self):
        windows = np.array([[1., 2., 3., 10., 20., 30.],
                            [3., 4., 5., 40., 50., 60.]])
        predicted = seasonal_naive_forecast(windows, 5, 3)
        np.testing.assert_array_equal(predicted, [[10., 20., 30., 10., 20.],
                                                  [40., 50., 60., 40., 50.]])

    def test_insufficient_history_rejected(self):
        with self.assertRaises(ValueError):
            seasonal_naive_forecast([[1., 2.]], 3, 24)

    def test_invalid_sample_and_horizon_rejected(self):
        with self.assertRaises(ValueError):
            seasonal_naive_forecast([[1., 2., np.nan]], 2, 2)
        with self.assertRaises(ValueError):
            seasonal_naive_forecast([[1., 2., 3.]], 0, 2)


if __name__ == '__main__':
    unittest.main()
