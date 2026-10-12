"""Provisional prediction contract for synthetic practice data.

Only a persistence *reference* is produced; this module does not train ML
models and is not an actual C2 model prediction or irrigation instruction.
"""
from datetime import datetime, timedelta, timezone
from math import isfinite

TARGETS = {
    "soil_moisture_pct": "%",
    "air_temperature_c": "degC",
    "relative_humidity_pct": "%",
}


def forecast_from_hourly(rows, plot_id, issued_at, lookback_hours=48,
                         horizon_hours=24, max_age_hours=2):
    """Forecast repeated last values if one plot has contiguous recent hourly history."""
    if not isinstance(issued_at, datetime) or issued_at.tzinfo is None or issued_at.utcoffset() is None:
        raise ValueError("issued_at must be timezone-aware datetime")
    if not isinstance(lookback_hours, int) or lookback_hours < 1:
        raise ValueError("lookback_hours must be positive integer")
    if not isinstance(horizon_hours, int) or horizon_hours < 1:
        raise ValueError("horizon_hours must be positive integer")
    if max_age_hours < 0:
        raise ValueError("max_age_hours cannot be negative")

    issued_at = issued_at.astimezone(timezone.utc)
    history = sorted((r for r in rows if r["plot_id"] == plot_id and
                      r.get("source") == "synthetic_practice" and
                      r["hour_end"] <= issued_at),
                     key=lambda r: r["hour_end"])

    payload = {
        "plot_id": plot_id,
        "issued_at": issued_at.isoformat(),
        "status": "unavailable",
        "reason": None,
        "source": "synthetic_practice",
        "model": "persistence_reference_not_trained",
        "model_version": "practice-0.1",
        "forecast": [],
        "input_end": None,
    }
    if not history:
        payload["reason"] = "no eligible observations"
        return payload
    last = history[-1]
    payload["input_end"] = last["hour_end"].isoformat()
    age = issued_at - last["hour_end"]
    if age > timedelta(hours=max_age_hours):
        payload["status"] = "stale"
        payload["reason"] = "most recent input is too old"
        return payload
    if len(history) < lookback_hours:
        payload["reason"] = "insufficient hourly history"
        return payload
    window = history[-lookback_hours:]
    if any(b["hour_start"] != a["hour_end"] for a, b in zip(window, window[1:])):
        payload["reason"] = "gaps in hourly history"
        return payload
    if not all(isfinite(row[key]) for row in window for key in TARGETS):
        payload["reason"] = "invalid numeric history"
        return payload
    payload["status"] = "provisional"
    for step in range(1, horizon_hours + 1):
        timestamp = last["hour_end"] + timedelta(hours=step)
        payload["forecast"].append({
            "target_end": timestamp.isoformat(),
            "values": {name: {"value": float(last[name]), "unit": unit}
                       for name, unit in TARGETS.items()},
        })
    return payload
