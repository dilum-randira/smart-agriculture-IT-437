"""Strict input contract for the *simulated* C1-to-C2 learning exercise.

No sensor data is collected. These sample fields are not a finalized C1 API.
"""

from datetime import datetime, timezone
from math import isfinite

REQUIRED_FIELDS = (
    "plot_id", "recorded_at", "soil_moisture_pct",
    "air_temperature_c", "relative_humidity_pct",
    "rainfall_mm", "source", "quality_flag",
)
STAGES = {"Vegetative", "Flowering", "Fruit_Set", "Harvesting"}
NUMERIC_RANGES = {
    "soil_moisture_pct": (0.0, 100.0),
    "air_temperature_c": (-20.0, 65.0),
    "relative_humidity_pct": (0.0, 100.0),
    "rainfall_mm": (0.0, None),
}


def parse_aware_datetime(value):
    """Return aware UTC datetime; reject naive timestamps and invalid values."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("recorded_at must be ISO 8601") from exc
    else:
        raise ValueError("recorded_at must be ISO 8601 text or datetime")
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp needs explicit timezone information")
    return dt.astimezone(timezone.utc)


def validate_reading(reading):
    """Validate and normalize a single explicitly synthetic practice reading."""
    if not isinstance(reading, dict):
        raise ValueError("reading must be a dictionary")
    missing = set(REQUIRED_FIELDS) - reading.keys()
    if missing:
        raise ValueError("missing required fields: " + ", ".join(sorted(missing)))
    if not isinstance(reading["plot_id"], str) or not reading["plot_id"].strip():
        raise ValueError("plot_id must be nonempty text")
    if reading["source"] != "synthetic_practice":
        raise ValueError("practice adapter accepts only synthetic_practice records")
    if reading["quality_flag"] not in ("valid", "invalid"):
        raise ValueError("quality_flag must be valid or invalid")
    stage = reading.get("growth_stage")
    if stage is not None and stage not in STAGES:
        raise ValueError("unsupported growth_stage")
    moment = parse_aware_datetime(reading["recorded_at"])
    fields = {}
    for name, (lower, upper) in NUMERIC_RANGES.items():
        value = reading[name]
        if type(value) not in (int, float) or not isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if value < lower or (upper is not None and value > upper):
            raise ValueError(f"{name} is outside permitted practice range")
        fields[name] = float(value)
    return {
        "plot_id": reading["plot_id"],
        "recorded_at": moment,
        "source": "synthetic_practice",
        "quality_flag": reading["quality_flag"],
        "growth_stage": stage,
        **fields,
    }
