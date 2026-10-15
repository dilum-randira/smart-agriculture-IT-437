"""Measured next-seven-day fresh harvest labels for plot/cycle issue times.

No synthetic target generation. Missing log coverage is NOT zero yield.
"""
from datetime import datetime, timedelta, timezone
from math import isfinite


def _time(value):
    if not isinstance(value, str):
        raise ValueError("timestamps must be ISO 8601 strings")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)


def next_week_fresh_yield(plot_id, cycle_id, issued_at, harvest_events, coverage_end):
    """Return a target only if the seven-day harvest log is fully covered.

    Each matched record must represent an actual measured fresh harvest;
    a zero target requires explicit complete observation coverage.
    """
    if not isinstance(plot_id, str) or not plot_id.strip():
        raise ValueError("plot_id required")
    if not isinstance(cycle_id, str) or not cycle_id.strip():
        raise ValueError("cycle_id required")
    origin = _time(issued_at)
    end = origin + timedelta(days=7)
    if _time(coverage_end) < end:
        return {"status": "unavailable", "reason": "harvest log does not cover target week", "fresh_yield_kg": None}
    total = 0.0
    count = 0
    identifiers = set()
    for event in harvest_events:
        if not isinstance(event, dict):
            raise ValueError("harvest event must be a mapping")
        if event.get("plot_id") != plot_id or event.get("cycle_id") != cycle_id:
            continue
        when = _time(event.get("harvested_at"))
        if not origin < when <= end:
            continue
        weight = event.get("fresh_mass_kg")
        if type(weight) not in (float, int) or not isfinite(weight) or weight < 0:
            raise ValueError("valid measured fresh harvest mass required")
        if event.get("measurement_type") != "measured_fresh_mass":
            raise ValueError("estimated or dry mass is not a fresh harvest label")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in identifiers:
            raise ValueError("unique harvest event_id required to prevent double counting")
        identifiers.add(event_id)
        total += float(weight)
        count += 1
    return {
        "status": "available", "fresh_yield_kg": total,
        "harvest_event_count": count, "plot_id": plot_id, "cycle_id": cycle_id,
        "issued_at": origin.isoformat(), "target_end": end.isoformat(),
        "unit": "kg_per_plot_over_next_7_days",
    }
