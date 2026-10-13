import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'practice'/'iot_replay'))
from replay import generate_readings
from audit import audit_readings
from hourly import aggregate_complete_hours

class AuditTests(unittest.TestCase):
    def test_pristine_4_slot_hour(self):
        result=audit_readings(generate_readings(hours=1))
        self.assertEqual(result['report']['accepted'],4)
        self.assertEqual(result['report']['received'],4)
        self.assertEqual(len(aggregate_complete_hours(result['accepted_readings'])),1)

    def test_duplicate_conflict_and_invalid_quarantined(self):
        records=list(generate_readings(hours=2))
        changed={**records[0], 'air_temperature_c': 15.0}
        flagged={**records[4], 'quality_flag':'invalid'}
        audit=audit_readings(records + [records[0], changed, flagged])
        self.assertEqual(audit['report']['received'], 11)
        self.assertEqual(audit['report']['duplicate'],1)
        self.assertEqual(audit['report']['conflicting_duplicate'],1)
        self.assertEqual(audit['report']['flagged_invalid'],1)
        self.assertEqual(audit['report']['accepted'],6)
        self.assertEqual(audit['report']['quarantined_slots'],2)
        self.assertEqual(aggregate_complete_hours(audit['accepted_readings']),[])

    def test_malformed_and_off_schedule_are_counted(self):
        records=list(generate_readings(hours=1))
        bad={**records[0], 'air_temperature_c': 1000}
        odd={**records[0], 'recorded_at': '2026-01-01T00:02:00+00:00'}
        audit=audit_readings(records+[bad,odd])
        self.assertEqual(audit['report']['malformed'],1)
        self.assertEqual(audit['report']['off_schedule'],1)
        self.assertEqual(audit['report']['accepted'],4)

    def test_conflict_is_order_independent(self):
        readings=list(generate_readings(hours=1))
        conflict={**readings[0], 'air_temperature_c': 17}
        a=audit_readings([conflict]+readings)['report']
        b=audit_readings(readings+[conflict])['report']
        self.assertEqual(a['accepted'],b['accepted'])
        self.assertEqual(a['quarantined_slots'],b['quarantined_slots'])

if __name__=='__main__':unittest.main()
