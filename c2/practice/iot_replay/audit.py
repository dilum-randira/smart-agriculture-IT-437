"""Auditable, conservative synthetic-input screening before hourly aggregation.

Duplicates are not counted as new measurements; conflicting copies of an
identical (plot_id, timestamp) are quarantined. Report uses no personal IDs.
"""
from collections import Counter
from schema import validate_reading

SLOTS = frozenset({0, 15, 30, 45})


def audit_readings(readings):
    """Return validated records and report on records rejected or quarantined."""
    counts = Counter()
    seen = {}
    quarantined = set()
    for raw in readings:
        counts['received'] += 1
        try:
            reading = validate_reading(raw)
        except (ValueError, TypeError, KeyError):
            counts['malformed'] += 1
            continue
        time = reading['recorded_at']
        if time.minute not in SLOTS or time.second or time.microsecond:
            counts['off_schedule'] += 1
            continue
        key = (reading['plot_id'], time)
        if reading['quality_flag'] != 'valid':
            counts['flagged_invalid'] += 1
            quarantined.add(key)
            continue
        if key in quarantined:
            counts['quarantined_repeats'] += 1
            continue
        if key in seen:
            if seen[key] == reading:
                counts['duplicate'] += 1
            else:
                counts['conflicting_duplicate'] += 1
                quarantined.add(key)
            continue
        seen[key] = reading
    accepted = [value for key, value in seen.items() if key not in quarantined]
    accepted.sort(key=lambda r: (r['plot_id'], r['recorded_at']))
    counts['accepted'] = len(accepted)
    counts['quarantined_slots'] = len(quarantined)
    return {
        'accepted_readings': accepted,
        'report': {name: counts[name] for name in (
            'received', 'accepted', 'malformed', 'off_schedule', 'flagged_invalid',
            'duplicate', 'conflicting_duplicate', 'quarantined_repeats',
            'quarantined_slots')},
        'source': 'synthetic_practice',
    }
