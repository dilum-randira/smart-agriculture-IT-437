import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "time_series"))
from plot_comparison import make_plots, read_practice_archive


class PlotComparisonTests(unittest.TestCase):
    def test_generates_two_pngs_from_synthetic_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.npz"
            actual = np.array([[10., 11., 12.], [13., 14., 15.]])
            kwargs = {name: actual + offset for name, offset in (
                ("persistence", 1), ("seasonal", 0), ("lstm", .2), ("gru", .3))}
            np.savez_compressed(
                path, actual=actual, synthetic_marker=np.array("SYNTHETIC_PRACTICE_ONLY"),
                variable=np.array("air_temperature_c"), **kwargs,
            )
            images = make_plots(path, Path(directory) / "images")
            self.assertEqual(len(images), 2)
            self.assertTrue(all(file.exists() and file.stat().st_size > 100 for file in images))
            with self.assertRaises(ValueError):
                make_plots(path, directory, example_index=100)

    def test_rejects_unlabelled_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.npz"
            actual = np.ones((2, 3))
            np.savez_compressed(path, actual=actual,
                synthetic_marker=np.array("REAL"), variable=np.array("air_temperature_c"),
                **{name: actual for name in ("persistence", "seasonal", "lstm", "gru")})
            with self.assertRaises(ValueError):
                read_practice_archive(path)


if __name__ == "__main__":
    unittest.main()
