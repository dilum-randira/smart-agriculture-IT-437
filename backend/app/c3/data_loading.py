"""Stage 2: load C3 input files, check them, and prepare daily values.

Works the same on the synthetic sample files and on real data later, as
long as the column names stay the same.

Typical use (from backend/):
    weather = load_weather(config.SAMPLE_DATA_DIR / "weather_synthetic_daily.csv")
"""

import json
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Required columns for each file (units are in the names)
# ---------------------------------------------------------------------------
WEATHER_COLUMNS = [
    "date", "tmax_c", "tmin_c", "rh_mean_pct", "rainfall_mm",
    "wind_speed_2m_ms", "solar_radiation_mj_m2_day",
]
SENSOR_COLUMNS = [
    "timestamp", "sensor_id", "soil_moisture_pct", "soil_temp_c", "air_temp_c",
    "air_humidity_pct", "light_lux", "rainfall_mm", "irrigation_logged_mm",
]
FORECAST_COLUMNS = [
    "issue_date", "target_date", "lead_day", "tmax_c", "tmin_c", "rh_mean_pct",
    "rainfall_mm", "wind_speed_2m_ms", "solar_radiation_mj_m2_day",
]

# ---------------------------------------------------------------------------
# Validity limits: (lowest allowed, highest allowed). None = no limit.
# Only limits that are true by definition or come from a datasheet are used.
# Tighter "realistic" limits need a source first (CLAUDE.md rule).
# ---------------------------------------------------------------------------
WEATHER_LIMITS = {
    "rh_mean_pct": (0.0, 100.0),            # relative humidity is 0-100 % by definition
    "rainfall_mm": (0.0, None),             # rain cannot be negative (definition)
    "wind_speed_2m_ms": (0.0, None),        # speed cannot be negative (definition)
    "solar_radiation_mj_m2_day": (0.0, None),  # radiation cannot be negative (definition)
}
SENSOR_LIMITS = {
    # Volumetric %, 0-100 by definition. TODO: replace with the measuring range
    # from the C1 soil moisture sensor's datasheet once the model is known
    # (this would also catch the synthetic 0 % and 99.9 % spikes). A
    # sudden-jump check is planned later; its threshold also needs a source.
    "soil_moisture_pct": (0.0, 100.0),
    "air_humidity_pct": (0.0, 100.0),       # relative humidity is 0-100 % by definition
    "light_lux": (0.0, 65535.0),            # BH1750 range (ROHM BH1750FVI datasheet)
    "rainfall_mm": (0.0, None),             # rain cannot be negative (definition)
    "irrigation_logged_mm": (0.0, None),    # water applied cannot be negative (definition)
}


# ---------------------------------------------------------------------------
# Checking helpers
# ---------------------------------------------------------------------------
def check_required_columns(df: pd.DataFrame, required: list[str], file_label: str) -> None:
    """Raise ValueError naming any required column that is missing."""
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{file_label} is missing columns: {missing}")


def count_missing_values(df: pd.DataFrame) -> dict[str, int]:
    """Number of blank cells in each column (only columns that have some)."""
    counts = df.isna().sum()
    return {col: int(n) for col, n in counts.items() if n > 0}


def find_out_of_range(df: pd.DataFrame, limits: dict) -> pd.DataFrame:
    """True where a value is outside its (low, high) limit. Blanks are False."""
    mask = pd.DataFrame(False, index=df.index, columns=list(limits))
    for col, (low, high) in limits.items():
        if low is not None:
            mask[col] |= df[col] < low
        if high is not None:
            mask[col] |= df[col] > high
    return mask


def blank_out_of_range(df: pd.DataFrame, limits: dict) -> tuple[pd.DataFrame, dict[str, int]]:
    """Replace impossible values with blanks (NaN).

    Returns the cleaned copy and how many values were blanked per column.
    The input DataFrame is not changed.
    """
    mask = find_out_of_range(df, limits)
    cleaned = df.copy()
    for col in limits:
        cleaned.loc[mask[col], col] = float("nan")
    counts = {col: int(mask[col].sum()) for col in limits if mask[col].any()}
    return cleaned, counts


def find_spikes(values: pd.Series, max_jump: float) -> pd.Series:
    """True where a reading jumps more than max_jump away from BOTH neighbours
    in opposite directions (up then straight back down, or the reverse).

    A real change (irrigation, rain) stays at its new level, so it is not
    flagged. max_jump (same unit as values) has NO default: it needs a source,
    e.g. the soil moisture sensor's datasheet or C1's calibration notes.
    Blank readings and the first/last reading are never flagged.
    """
    step_in = values.diff()                 # change from the previous reading
    step_out = values.shift(-1) - values    # change to the next reading
    spike = (step_in.abs() > max_jump) & (step_out.abs() > max_jump) & (step_in * step_out < 0)
    return spike.fillna(False).astype(bool)


# ---------------------------------------------------------------------------
# Loaders (one per file)
# ---------------------------------------------------------------------------
def load_weather(path: Path) -> pd.DataFrame:
    """Daily weather CSV -> DataFrame with a datetime 'date' column."""
    df = pd.read_csv(path)
    check_required_columns(df, WEATHER_COLUMNS, Path(path).name)
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_sensors(path: Path) -> pd.DataFrame:
    """15-minute C1 sensor CSV -> DataFrame with a datetime 'timestamp' column."""
    df = pd.read_csv(path)
    check_required_columns(df, SENSOR_COLUMNS, Path(path).name)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def load_forecasts(path: Path) -> pd.DataFrame:
    """C2 7-day forecast CSV -> DataFrame with datetime issue/target dates."""
    df = pd.read_csv(path)
    check_required_columns(df, FORECAST_COLUMNS, Path(path).name)
    df["issue_date"] = pd.to_datetime(df["issue_date"])
    df["target_date"] = pd.to_datetime(df["target_date"])
    return df


def load_plot_config(path: Path) -> dict:
    """Plot and soil settings JSON -> dict. Checks the soil values make sense."""
    with open(path, encoding="utf-8") as f:
        plot = json.load(f)
    soil = plot["soil"]
    # Wilting point must be below field capacity (definition of available water).
    if not soil["wilting_point_m3m3"] < soil["field_capacity_m3m3"]:
        raise ValueError("wilting_point_m3m3 must be smaller than field_capacity_m3m3")
    return plot


# ---------------------------------------------------------------------------
# Preparing sensor data
# ---------------------------------------------------------------------------
def add_soil_moisture_m3m3(sensors: pd.DataFrame) -> pd.DataFrame:
    """Add soil_moisture_m3m3 = soil_moisture_pct / 100 (volumetric % -> m3/m3)."""
    out = sensors.copy()
    out["soil_moisture_m3m3"] = out["soil_moisture_pct"] / 100.0
    return out


def daily_sensor_summary(sensors: pd.DataFrame) -> pd.DataFrame:
    """Turn 15-minute readings into one row per day.

    Run blank_out_of_range first so impossible values are not averaged in.
    Blank readings are skipped; 'soil_moisture_readings' shows how many
    valid readings each day had (96 = a full day at 15-minute intervals).
    """
    by_day = sensors.set_index("timestamp").resample("D")
    daily = pd.DataFrame({
        "soil_moisture_mean_pct": by_day["soil_moisture_pct"].mean(),
        "soil_moisture_readings": by_day["soil_moisture_pct"].count(),
        "air_temp_max_c": by_day["air_temp_c"].max(),
        "air_temp_min_c": by_day["air_temp_c"].min(),
        "air_humidity_mean_pct": by_day["air_humidity_pct"].mean(),
        "rainfall_mm_day": by_day["rainfall_mm"].sum(),
        "irrigation_mm_day": by_day["irrigation_logged_mm"].sum(),
    })
    daily.index.name = "date"
    return daily.reset_index()
