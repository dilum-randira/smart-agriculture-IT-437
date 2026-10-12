"""Aggregate COMPLETE hourly groups; rainfall is a sum, other fields means.

This strict practice aggregation requires four distinct readings at 00/15/30/45.
Irregular/gapped hours are excluded rather than silently imputed.
"""
from collections import defaultdict
from datetime import timedelta
from statistics import mean

from schema import validate_reading

AVERAGED = ("soil_moisture_pct", "air_temperature_c", "relative_humidity_pct")


def aggregate_complete_hours(readings):
    groups = defaultdict(dict)
    for raw in readings:
        item = validate_reading(raw)
        if item["quality_flag"] != "valid":
            continue
        moment = item["recorded_at"]
        hour = moment.replace(minute=0, second=0, microsecond=0)
        if moment.second or moment.microsecond or moment.minute not in (0, 15, 30, 45):
            continue
        key = (item["plot_id"], hour)
        # Deduplicate repeated records without inflating sample size.
        # Conflicting duplicates invalidate this slot for conservative handling.
        existing = groups[key].get(moment.minute)
        if existing is None and moment.minute not in groups[key]:
            groups[key][moment.minute] = item
        elif existing != item:
            groups[key][moment.minute] = None

    result = []
    for (plot, hour), slots in groups.items():
        if set(slots) != {0, 15, 30, 45} or any(v is None for v in slots.values()):
            continue
        values = [slots[m] for m in (0, 15, 30, 45)]
        row = {
            "plot_id": plot,
            "hour_start": hour,
            "hour_end": hour + timedelta(hours=1),
            "rainfall_mm": sum(v["rainfall_mm"] for v in values),
            "source": "synthetic_practice",
            "record_count": 4,
        }
        for field in AVERAGED:
            row[field] = mean(v[field] for v in values)
        result.append(row)
    return sorted(result, key=lambda x: (x["plot_id"], x["hour_start"]))
