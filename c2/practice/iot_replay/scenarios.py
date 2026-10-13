"""Executable synthetic C1->C2 quality and prediction-availability scenarios.

This module intentionally does not read an IoT device or train an ML model.
"""
import json
from datetime import timedelta

from audit import audit_readings
from contracts import publishable_payload
from forecast import forecast_from_hourly
from hourly import aggregate_complete_hours
from replay import generate_readings


def scenario_report():
    records = list(generate_readings(hours=72))
    original = audit_readings(records)
    hourly = aggregate_complete_hours(original['accepted_readings'])
    issue_time = hourly[-1]['hour_end'] + timedelta(minutes=5)

    conflict = {**records[-8], 'air_temperature_c': 12.0}
    damaged = audit_readings(records + [conflict])
    damaged_hourly = aggregate_complete_hours(damaged['accepted_readings'])

    definitions = {
        'complete_history': (hourly, issue_time),
        'conflicting_input_gap': (damaged_hourly, issue_time),
        'stale_input': (hourly, issue_time + timedelta(hours=5)),
        'short_history': (hourly[:20], hourly[19]['hour_end']),
    }
    output = {}
    for label, (rows, issued) in definitions.items():
        raw = forecast_from_hourly(rows, 'practice_plot_01', issued)
        contract = publishable_payload(raw)
        output[label] = {
            'status': contract['status'],
            'reason': contract['reason'],
            'eligible_hours': len(rows),
            'prediction_rows': len(contract['predictions']),
        }
    return {
        'source': 'synthetic_practice',
        'warning': 'Not actual IoT readings or learned ML forecasts',
        'normal_input_audit': original['report'],
        'conflict_input_audit': damaged['report'],
        'scenarios': output,
    }


if __name__ == '__main__':
    print(json.dumps(scenario_report(), indent=2))
