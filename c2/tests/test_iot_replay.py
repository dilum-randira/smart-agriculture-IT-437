import sys
import unittest
from pathlib import Path
from datetime import timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "practice" / "iot_replay"))
from replay import generate_readings, replay_one_by_one


class ReplayTests(unittest.TestCase):
    def test_quarter_hourly_replay(self):
        readings = list(generate_readings(hours=2))
        self.assertEqual(len(readings), 8)
        self.assertEqual(readings[1]["recorded_at"] - readings[0]["recorded_at"], timedelta(minutes=15))
        self.assertEqual(readings[0]["source"], "synthetic_practice")

    def test_reproducible_and_callback(self):
        self.assertEqual(list(generate_readings(hours=1)), list(generate_readings(hours=1)))
        observed = []
        self.assertEqual(replay_one_by_one(observed.append, hours=1), 4)
        self.assertEqual(len(observed), 4)

    def test_invalid_hours_rejected(self):
        with self.assertRaises(ValueError):
            list(generate_readings(hours=0))


if __name__ == "__main__":
    unittest.main()
