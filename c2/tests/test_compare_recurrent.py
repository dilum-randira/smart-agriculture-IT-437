import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "time_series"))
from compare_recurrent import prepare_practice_windows, make_recurrent_model


class CompareRecurrentTests(unittest.TestCase):
    def test_same_test_targets_and_training_scaler(self):
        raw, scaled, scaler = prepare_practice_windows()
        self.assertEqual(raw["test"]["X"].shape, (69, 48))
        self.assertEqual(raw["test"]["y"].shape, (69, 24))
        self.assertEqual(scaled["test"]["X"].shape, (69, 48, 1))
        self.assertEqual(len(scaled["train"]["X"]), 324)
        self.assertEqual(scaler.n_features_in_, 1)

    def test_invalid_architecture_rejected(self):
        with self.assertRaises(ValueError):
            make_recurrent_model(None, "CNN")


if __name__ == "__main__":
    unittest.main()
