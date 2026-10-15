"""Training-input checks for a proposed C1 -> C2 schema.

This does not collect C1 data, calibrate hardware, or claim field deployment.
"""
from datetime import datetime, timezone
from math import isfinite

MEASUREMENTS = {
    "air_temperature_c": (-30.0, 65.0),
    "relative_humidity_pct": (0.0, 100.0),
}


def validate_c2_observation(payload):
    """Return canonical observation; reject ambiguous units and provenance."""
    if not isinstance(payload, dict):
        raise ValueError("observation must be a mapping")
    plot_id = payload.get("plot_id")
    if not isinstance(plot_id, str) or not plot_id.strip():
        raise ValueError("plot_id must be nonblank")
    stamp = payload.get("timestamp")
    if not isinstance(stamp, str):
        raise ValueError("timestamp must be an ISO 8601 string")
    try:
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO 8601") from exc
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("timestamp must include an offset")
    if payload.get("quality_flag") not in ("measured_valid", "corrected_valid"):
        raise ValueError("only eligible quality-flagged observations are accepted")
    source = payload.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source provenance required")
    values = {}
    for name, (low, high) in MEASUREMENTS.items():
        val = payload.get(name)
        if type(val) not in (int, float) or not isfinite(val) or not low <= val <= high:
            raise ValueError(f"invalid {name}")
        values[name] = float(val)
    moisture = payload.get("soil_moisture")
    if type(moisture) not in (int, float) or not isfinite(moisture):
        raise ValueError("soil_moisture must be numeric and finite")
    unit = payload.get("soil_moisture_unit")
    if unit not in ("percent_calibrated", "m3_per_m3", "kPa"):
        raise ValueError("explicit calibrated soil-moisture unit required")
    if (unit == "percent_calibrated" and not 0 <= moisture <= 100) or (
        unit == "m3_per_m3" and not 0 <= moisture <= 1
    ) or (unit == "kPa" and moisture < 0):
        raise ValueError("soil-moisture reading outside declared-unit range")
    calibration = payload.get("calibration_version")
    if not isinstance(calibration, str) or not calibration.strip():
        raise ValueError("calibration_version required")
    return {
        "plot_id": plot_id.strip(),
        "timestamp": when.astimezone(timezone.utc).isoformat(),
        "quality_flag": payload["quality_flag"],
        "source": source,
        "calibration_version": calibration,
        "soil_moisture": float(moisture),
        "soil_moisture_unit": unit,
        **values,
    }
