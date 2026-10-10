import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "time_series"))
from windows import chronological_windows
from scaling import fit_train_only_scaler, inverse_forecast, transform_splits


class ScalingTests(unittest.TestCase):
    def test_future_data_does_not_change_training_scaler(self):
        values = np.arange(1000.0)
        splits = chronological_windows(values)
        original_scaler = fit_train_only_scaler(splits)
        another = values.copy()
        another[850:] += 100_000  # values restricted to test section
        altered_splits = chronological_windows(another)
        changed_scaler = fit_train_only_scaler(altered_splits)
        self.assertEqual(float(original_scaler.mean_[0]), float(changed_scaler.mean_[0]))
        transformed = transform_splits(splits, original_scaler)
        self.assertEqual(transformed["train"]["X"].shape[-1], 1)
        np.testing.assert_allclose(
            inverse_forecast(transformed["test"]["y"], original_scaler),
            splits["test"]["y"], atol=1e-10,
        )


if __name__ == "__main__":
    unittest.main()
