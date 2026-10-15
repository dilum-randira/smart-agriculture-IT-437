"""Strict C2 output checker for downstream C3 / C4 handoffs.

Schema validation only; not a trained forecast or production service.
"""
from datetime import datetime, timezone
from math import isfinite

ALLOWED_STATUSES = {"valid", "provisional", "stale", "unavailable"}
MICROCLIMATE = {"air_temperature_c": "degC", "relative_humidity_pct": "pct"}
YIELD = {"fresh_yield_kg_next_7_days": "kg_per_plot"}


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone offset required")
    return dt.astimezone(timezone.utc)


def validate_prediction(payload, consumer):
    """Normalize one prediction row; reject fabricated intervals and bad timing."""
    if consumer not in {"c3", "c4"} or not isinstance(payload, dict):
        raise ValueError("consumer c3/c4 and mapping payload required")
    for name in ("prediction_id", "plot_id", "model_version", "data_version", "source"):
        if not isinstance(payload.get(name), str) or not payload[name].strip():
            raise ValueError(f"missing {name}")
    if payload.get("status") not in ALLOWED_STATUSES:
        raise ValueError("unknown prediction status")
    issued = _timestamp(payload.get("issued_at"))
    start = _timestamp(payload.get("target_start"))
    end = _timestamp(payload.get("target_end"))
    if end <= start or end <= issued:
        raise ValueError("prediction target must be future and have positive duration")
    variable = payload.get("variable")
    if consumer == "c3":
        if variable != "soil_moisture" and variable not in MICROCLIMATE:
            raise ValueError("unsupported C3 forecast variable")
        if variable in MICROCLIMATE and payload.get("unit") != MICROCLIMATE[variable]:
            raise ValueError("unit mismatch")
        if variable == "soil_moisture" and payload.get("unit") not in ("percent_calibrated", "m3_per_m3", "kPa"):
            raise ValueError("soil moisture unit must be explicit")
    elif variable not in YIELD or payload.get("unit") != YIELD[variable]:
        raise ValueError("C4 yield contract expects fresh kg/plot")
    numbers = [payload.get(k) for k in ("lower", "median", "upper")]
    status = payload["status"]
    if status in {"stale", "unavailable"}:
        if any(x is not None for x in numbers):
            raise ValueError("stale/unavailable must not contain current actionable predictions")
    elif numbers[1] is None or type(numbers[1]) not in (int, float) or not isfinite(numbers[1]):
        raise ValueError("active prediction must have a finite median")
    if any(x is not None for x in (numbers[0], numbers[2])):
        if any(type(x) not in (float, int) or not isfinite(x) for x in numbers):
            raise ValueError("complete finite bounds and median required")
        if not numbers[0] <= numbers[1] <= numbers[2]:
            raise ValueError("crossed prediction quantiles")
        if payload.get("interval_level") != 0.9:
            raise ValueError("only declared 90 percent interval supported here")
    elif payload.get("interval_level") is not None:
        raise ValueError("interval level cannot be declared without bounds")
    return {**payload, "issued_at": issued.isoformat(), "target_start": start.isoformat(), "target_end": end.isoformat()}
