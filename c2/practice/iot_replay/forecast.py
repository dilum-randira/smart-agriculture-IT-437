"""Provisional persistence reference using only eligible synthetic practice inputs.

This is not a trained model and makes no real-farm accuracy claim.
"""
from datetime import datetime, timedelta, timezone
from math import isfinite

TARGETS = {'soil_moisture_pct': '%', 'air_temperature_c': 'degC', 'relative_humidity_pct': '%'}


def forecast_from_hourly(rows, plot_id, issued_at, lookback_hours=48,
                         horizon_hours=24, max_age_hours=2):
    """Return future-aligned reference steps; never forecast timestamps at/before issue."""
    if not isinstance(issued_at, datetime) or issued_at.tzinfo is None or issued_at.utcoffset() is None:
        raise ValueError('issued_at must be timezone-aware datetime')
    if type(lookback_hours) is not int or lookback_hours < 1:
        raise ValueError('lookback_hours must be positive integer')
    if type(horizon_hours) is not int or horizon_hours < 1:
        raise ValueError('horizon_hours must be positive integer')
    if not isinstance(max_age_hours, (int, float)) or not isfinite(max_age_hours) or max_age_hours < 0:
        raise ValueError('max_age_hours must be finite and nonnegative')

    issued_at = issued_at.astimezone(timezone.utc)
    history = sorted((r for r in rows if r['plot_id'] == plot_id and
                      r.get('source') == 'synthetic_practice' and
                      r['hour_end'] <= issued_at), key=lambda r: r['hour_end'])
    payload = {
        'plot_id': plot_id, 'issued_at': issued_at.isoformat(),
        'status': 'unavailable', 'reason': None, 'source': 'synthetic_practice',
        'model': 'persistence_reference_not_trained', 'model_version': 'practice-0.2',
        'forecast': [], 'input_end': None, 'forecast_origin': None,
    }
    if not history:
        payload['reason'] = 'no eligible observations'
        return payload
    last = history[-1]
    payload['input_end'] = last['hour_end'].isoformat()
    age = issued_at - last['hour_end']
    if age > timedelta(hours=max_age_hours):
        payload['status'] = 'stale'
        payload['reason'] = 'most recent input is too old'
        return payload
    if len(history) < lookback_hours:
        payload['reason'] = 'insufficient hourly history'
        return payload
    window = history[-lookback_hours:]
    if any(b['hour_start'] != a['hour_end'] for a, b in zip(window, window[1:])):
        payload['reason'] = 'gaps in hourly history'
        return payload
    if not all(isfinite(row[key]) for row in window for key in TARGETS):
        payload['reason'] = 'invalid numeric history'
        return payload
    # Anchor forecasts to the latest issue time, not the last available reading;
    # missing recent observations must never yield target times in the past.
    origin = issued_at.replace(minute=0, second=0, microsecond=0)
    payload['forecast_origin'] = origin.isoformat()
    payload['status'] = 'provisional'
    for step in range(1, horizon_hours + 1):
        target_end = origin + timedelta(hours=step)
        payload['forecast'].append({
            'target_end': target_end.isoformat(),
            'values': {name: {'value': float(last[name]), 'unit': unit}
                       for name, unit in TARGETS.items()},
        })
    return payload
