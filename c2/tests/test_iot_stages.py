import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'practice'/'iot_replay'))
from stages import stage_as_of,validate_stage_event

def event(stage, observed,recorded,plot='plot-a'):
    return {'plot_id':plot,'growth_stage':stage,
            'observed_at': observed+'+00:00','recorded_at':recorded+'+00:00'}

class StageTests(unittest.TestCase):
    def test_never_uses_future_growth_stage_or_late_entry(self):
        data=[event('Vegetative','2026-01-01T08:00:00','2026-01-01T08:30:00'),
              event('Flowering','2026-01-02T07:00:00','2026-01-03T12:00:00'),
              event('Fruit_Set','2026-01-05T09:00:00','2026-01-05T09:00:00')]
        self.assertIsNone(stage_as_of(data,'plot-a','2026-01-01T08:00:00+00:00'))
        self.assertEqual(stage_as_of(data,'plot-a','2026-01-03T00:00:00+00:00')['growth_stage'],'Vegetative')
        self.assertEqual(stage_as_of(data,'plot-a','2026-01-03T12:00:00+00:00')['growth_stage'],'Flowering')
        self.assertIsNone(stage_as_of(data,'plot-b','2026-01-04T00:00:00+00:00'))

    def test_invalid_stage_and_timestamp(self):
        bad=event('Unknown','2026-01-01T08:00:00','2026-01-01T09:00:00')
        with self.assertRaises(ValueError):validate_stage_event(bad)
        bad=event('Flowering','2026-01-01T09:00:00','2026-01-01T08:00:00')
        with self.assertRaises(ValueError):validate_stage_event(bad)

if __name__=='__main__':unittest.main()
