import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "time_series"))
from windows import chronological_windows


class WindowsTests(unittest.TestCase):
    def test_targets_do_not_cross_boundaries(self):
        series = np.arange(1000.0)
        lookback, horizon = 48, 24
        splits = chronological_windows(series, lookback, horizon, stride=12)
        a = splits["boundaries"]["train_end"]
        b = splits["boundaries"]["validation_end"]
        self.assertTrue(np.all(splits["train"]["origins"] + horizon <= a))
        self.assertTrue(np.all(splits["validation"]["origins"] >= a))
        self.assertTrue(np.all(splits["validation"]["origins"] + horizon <= b))
        self.assertTrue(np.all(splits["test"]["origins"] >= b))
        for split in ("train", "validation", "test"):
            x, y = splits[split]["X"], splits[split]["y"]
            self.assertEqual(x.shape[1], lookback)
            self.assertEqual(y.shape[1], horizon)
            np.testing.assert_array_equal(y[:, 0], x[:, -1] + 1)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            chronological_windows([1.0, np.nan] * 100)
        with self.assertRaises(ValueError):
            chronological_windows(range(100), lookback=48, horizon=24)


if __name__ == "__main__":
    unittest.main()
