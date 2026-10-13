import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'practice'/'iot_replay'))
from scenarios import scenario_report


class ScenarioTests(unittest.TestCase):
    def test_availability_responses(self):
        report=scenario_report()
        self.assertEqual(report['scenarios']['complete_history']['status'],'provisional')
        self.assertEqual(report['scenarios']['complete_history']['prediction_rows'],72)
        self.assertEqual(report['scenarios']['conflicting_input_gap']['status'],'unavailable')
        self.assertEqual(report['scenarios']['conflicting_input_gap']['prediction_rows'],0)
        self.assertEqual(report['scenarios']['stale_input']['status'],'stale')
        self.assertEqual(report['scenarios']['short_history']['status'],'unavailable')

    def test_scenarios_are_serializable_and_consistent(self):
        report=scenario_report()
        self.assertIn('synthetic',report['source'])
        self.assertEqual(report,json.loads(json.dumps(report)))
        self.assertEqual(report['conflict_input_audit']['quarantined_slots'],1)

if __name__=='__main__':unittest.main()
