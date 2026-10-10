import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "time_series"))
from persistence import persistence_forecast, horizon_scores


class PersistenceTests(unittest.TestCase):
    def test_repeat_latest_input_without_training(self):
        x = np.array([[10., 11., 12.], [20., 21., 22.]])
        got = persistence_forecast(x, 4)
        np.testing.assert_array_equal(got, [[12., 12., 12., 12.], [22., 22., 22., 22.]])

    def test_scores_are_zero_for_perfect_predictions(self):
        y = np.array([[1., 2., 3.], [4., 5., 6.]])
        for score in horizon_scores(y, y, horizons=(1, 3)).values():
            self.assertEqual(score["MAE"], 0.)
            self.assertEqual(score["RMSE"], 0.)

    def test_invalid_horizon_rejected(self):
        with self.assertRaises(ValueError):
            horizon_scores(np.zeros((2, 2)), np.zeros((2, 2)), horizons=(3,))


if __name__ == "__main__":
    unittest.main()
