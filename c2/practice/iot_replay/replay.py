"""Replay synthetic quarter-hourly readings; never claims live C1 hardware."""
from datetime import datetime, timedelta, timezone
from math import pi, sin
from schema import validate_reading


def generate_readings(hours=72, plot_id="practice_plot_01", start=None):
    if not isinstance(hours, int) or hours <= 0:
        raise ValueError("hours must be positive integer")
    if not isinstance(plot_id, str) or not plot_id.strip():
        raise ValueError("plot_id required")
    if start is None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start must have timezone")
    for i in range(hours * 4):
        when = start + timedelta(minutes=15 * i)
        daily_phase = 2 * pi * ((i % 96) / 96)
        reading = {
            "plot_id": plot_id,
            "recorded_at": when.isoformat(),
            "soil_moisture_pct": 32 + 3 * sin(daily_phase + 1),
            "air_temperature_c": 29 + 4 * sin(daily_phase),
            "relative_humidity_pct": 72 - 10 * sin(daily_phase),
            "rainfall_mm": 0.0,
            "source": "synthetic_practice",
            "quality_flag": "valid",
            "growth_stage": "Vegetative",
        }
        yield validate_reading(reading)


def replay_one_by_one(on_reading, hours=72):
    """Replay synchronously, without pretending actual wall-clock live sensing."""
    count = 0
    for reading in generate_readings(hours=hours):
        on_reading(reading)
        count += 1
    return count
