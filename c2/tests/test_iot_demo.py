import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "iot_replay"))
from demo import run_demo


class DemoTests(unittest.TestCase):
    def test_valid_demo_produces_provisional_reference(self):
        report = run_demo()
        self.assertEqual(report["received_records"], 72 * 4)
        self.assertEqual(report["eligible_complete_hours"], 72)
        self.assertEqual(report["prediction"]["status"], "provisional")
        self.assertEqual(len(report["prediction"]["forecast"]), 24)

    def test_missing_demo_marks_gap_unavailable(self):
        report = run_demo(mode="missing")
        self.assertEqual(report["eligible_complete_hours"], 71)
        self.assertEqual(report["prediction"]["status"], "unavailable")
        self.assertEqual(report["prediction"]["forecast"], [])

    def test_not_enough_history_is_unavailable(self):
        report = run_demo(hours=3)
        self.assertEqual(report["prediction"]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
