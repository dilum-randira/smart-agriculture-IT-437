"""Stage 10: real weather inputs from Open-Meteo, and the C2 prediction format.

Why: C2's handoff note (feature/c2-ml-foundation) says C2 forecasts soil
moisture, air temperature and RH only. FAO-56 ET0 also needs rain, wind and
solar radiation, so those come from an external weather service.

Open-Meteo (https://open-meteo.com), free for non-commercial use; cite
Open-Meteo and its sources. History: ERA5 reanalysis via the archive API
(0.25 deg, "Generated using Copernicus Climate Change Service information").
Variable names and units were checked against the live API (2026-10-21):
temperatures degC, humidity %, precipitation mm, wind m/s (with
wind_speed_unit=ms) at 10 m, shortwave radiation MJ/m2.

Parsing is separate from downloading so it can be tested offline.
"""

from typing import Callable

import pandas as pd

from app.c3 import et0 as et0_module

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARIABLES = [
    "temperature_2m_max", "temperature_2m_min", "relative_humidity_2m_max",
    "relative_humidity_2m_min", "relative_humidity_2m_mean", "precipitation_sum",
    "wind_speed_10m_mean", "shortwave_radiation_sum", "et0_fao_evapotranspiration",
]
OPEN_METEO_WIND_HEIGHT_M = 10.0   # wind_speed_10m_* is measured at 10 m (variable name)

# Open-Meteo name -> C3 column name (units already match C3)
RENAME = {
    "temperature_2m_max": "tmax_c",
    "temperature_2m_min": "tmin_c",
    "relative_humidity_2m_max": "rh_max_pct",
    "relative_humidity_2m_min": "rh_min_pct",
    "relative_humidity_2m_mean": "rh_mean_pct",
    "precipitation_sum": "rainfall_mm",
    "shortwave_radiation_sum": "solar_radiation_mj_m2_day",
    "et0_fao_evapotranspiration": "open_meteo_et0_mm_day",   # kept for cross-checking
}


def request_params(latitude_deg: float, longitude_deg: float, **extra) -> dict:
    """Query parameters for an Open-Meteo daily request (wind in m/s, local time)."""
    return {"latitude": latitude_deg, "longitude": longitude_deg,
            "daily": ",".join(DAILY_VARIABLES), "timezone": "auto",
            "wind_speed_unit": "ms", **extra}


def parse_open_meteo_daily(response_json: dict) -> pd.DataFrame:
    """Open-Meteo JSON -> C3 daily weather table (same columns as load_weather,
    plus rh_max_pct, rh_min_pct and open_meteo_et0_mm_day).

    Wind is converted from 10 m to 2 m with FAO-56 Eq. 47.
    """
    daily = response_json.get("daily")
    if not daily or "time" not in daily:
        raise ValueError("response has no daily data")
    missing = [v for v in DAILY_VARIABLES if v not in daily]
    if missing:
        raise ValueError(f"response is missing daily variables: {missing}")
    table = pd.DataFrame(daily).rename(columns=RENAME)
    table["date"] = pd.to_datetime(table.pop("time"))
    table["wind_speed_2m_ms"] = et0_module.wind_speed_at_2m_m_s(
        table.pop("wind_speed_10m_mean"), OPEN_METEO_WIND_HEIGHT_M)
    return table


def fetch_daily(url: str, params: dict, get: Callable | None = None) -> pd.DataFrame:
    """Download and parse one Open-Meteo request. `get` defaults to requests.get
    (tests pass a fake one so no internet is needed)."""
    if get is None:
        import requests
        get = requests.get
    response = get(url, params=params, timeout=30)
    response.raise_for_status()
    return parse_open_meteo_daily(response.json())


def fetch_forecast(latitude_deg: float, longitude_deg: float, days: int = 8,
                   get: Callable | None = None) -> pd.DataFrame:
    """Daily weather forecast for today and the next days (Open-Meteo forecast API)."""
    return fetch_daily(FORECAST_URL, request_params(latitude_deg, longitude_deg,
                                                    forecast_days=days), get)


def fetch_history(latitude_deg: float, longitude_deg: float, start_date: str, end_date: str,
                  get: Callable | None = None) -> pd.DataFrame:
    """Daily historical weather, ERA5 reanalysis (Open-Meteo archive API)."""
    return fetch_daily(ARCHIVE_URL, request_params(latitude_deg, longitude_deg,
                                                   start_date=start_date, end_date=end_date), get)


def to_c3_forecasts(daily: pd.DataFrame, issue_date: str) -> pd.DataFrame:
    """A daily forecast table -> the C3 forecast format used by
    optimiser.forecast_scenarios (issue_date, target_date, lead_day, ...).
    Days after issue_date become lead days 1, 2, 3, ..."""
    issue = pd.Timestamp(issue_date)
    ahead = daily[daily["date"] > issue].sort_values("date").copy()
    ahead["issue_date"] = issue
    ahead["target_date"] = ahead.pop("date")
    ahead["lead_day"] = (ahead["target_date"] - issue).dt.days
    return ahead.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Past forecasts as they were issued (Open-Meteo Previous Runs API)
# ---------------------------------------------------------------------------
# "_previous_dayN" = the value predicted N x 24 h before the valid time
# (N = 1..7), archived from January 2024 for most models. HOURLY only, so
# daily values are built here. Checked against the live API 2026-10-21:
# temperature degC, humidity %, precipitation mm per hour, wind m/s at 10 m,
# shortwave radiation W/m2 averaged over the past hour; Asia/Colombo time.
PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
PREVIOUS_RUN_BASES = ["temperature_2m", "relative_humidity_2m", "precipitation",
                      "wind_speed_10m", "shortwave_radiation"]
LEAD_DAYS = range(1, 8)
SECONDS_PER_HOUR = 3600.0                    # definition
JOULES_PER_MJ = 1_000_000.0                  # definition
HOURS_PER_DAY = 24


def previous_runs_params(latitude_deg: float, longitude_deg: float, start_date: str,
                         end_date: str) -> dict:
    """Query parameters asking for every variable at lead days 1..7."""
    hourly = [f"{base}_previous_day{n}" for base in PREVIOUS_RUN_BASES for n in LEAD_DAYS]
    return {"latitude": latitude_deg, "longitude": longitude_deg, "hourly": ",".join(hourly),
            "start_date": start_date, "end_date": end_date, "timezone": "auto",
            "wind_speed_unit": "ms"}


def daily_from_hourly(hourly: pd.DataFrame, suffix: str) -> pd.DataFrame:
    """Hourly values (columns <base><suffix>) -> one row per complete day.

    Daily max/min come from the hourly values (an approximation of the true
    extremes). Radiation: sum of hourly mean W/m2 x 3600 s -> MJ/m2/day.
    Wind: daily mean at 10 m -> 2 m with FAO-56 Eq. 47. Days with any
    missing hour are dropped.
    """
    col = {base: f"{base}{suffix}" for base in PREVIOUS_RUN_BASES}
    table = hourly.assign(date=hourly["time"].dt.normalize())
    complete = table.groupby("date")[list(col.values())].count().min(axis=1) == HOURS_PER_DAY
    by_day = table.groupby("date")
    daily = pd.DataFrame({
        "tmax_c": by_day[col["temperature_2m"]].max(),
        "tmin_c": by_day[col["temperature_2m"]].min(),
        "rh_max_pct": by_day[col["relative_humidity_2m"]].max(),
        "rh_min_pct": by_day[col["relative_humidity_2m"]].min(),
        "rh_mean_pct": by_day[col["relative_humidity_2m"]].mean(),
        "rainfall_mm": by_day[col["precipitation"]].sum(),
        "wind_speed_2m_ms": et0_module.wind_speed_at_2m_m_s(
            by_day[col["wind_speed_10m"]].mean(), OPEN_METEO_WIND_HEIGHT_M),
        "solar_radiation_mj_m2_day": by_day[col["shortwave_radiation"]].sum()
                                     * SECONDS_PER_HOUR / JOULES_PER_MJ,
    })
    return daily[complete].reset_index()


def parse_previous_runs(response_json: dict) -> pd.DataFrame:
    """Previous Runs JSON -> C3 forecast table (issue_date, target_date,
    lead_day, weather columns). The forecast for target day D at lead L is
    treated as issued on day D - L."""
    hourly = response_json.get("hourly")
    if not hourly or "time" not in hourly:
        raise ValueError("response has no hourly data")
    table = pd.DataFrame(hourly)
    table["time"] = pd.to_datetime(table["time"])
    parts = []
    for lead in LEAD_DAYS:
        suffix = f"_previous_day{lead}"
        missing = [f"{b}{suffix}" for b in PREVIOUS_RUN_BASES if f"{b}{suffix}" not in table]
        if missing:
            raise ValueError(f"response is missing hourly variables: {missing}")
        daily = daily_from_hourly(table, suffix).rename(columns={"date": "target_date"})
        daily["lead_day"] = lead
        daily["issue_date"] = daily["target_date"] - pd.to_timedelta(lead, unit="D")
        parts.append(daily)
    forecasts = pd.concat(parts, ignore_index=True)
    return forecasts.sort_values(["issue_date", "lead_day"]).reset_index(drop=True)


def fetch_previous_runs(latitude_deg: float, longitude_deg: float, start_date: str,
                        end_date: str, get: Callable | None = None) -> pd.DataFrame:
    """Past forecasts (lead days 1..7) for target days start_date..end_date."""
    if get is None:
        import requests
        get = requests.get
    response = get(PREVIOUS_RUNS_URL, params=previous_runs_params(
        latitude_deg, longitude_deg, start_date, end_date), timeout=120)
    response.raise_for_status()
    return parse_previous_runs(response.json())


# ---------------------------------------------------------------------------
# C2 predictions (proposed contract, c2/docs/team_data_handoff_v0.md - draft)
# ---------------------------------------------------------------------------
C2_KEYS = ["prediction_id", "plot_id", "issued_at", "target_start", "target_end", "variable",
           "unit", "median", "lower", "upper", "interval_level", "model_version",
           "data_version", "status"]


def parse_c2_predictions(records: list[dict]) -> pd.DataFrame:
    """C2 prediction records -> table. Checks the proposed keys are present.

    Missing intervals stay null (the contract says never fabricate them).
    """
    table = pd.DataFrame(records)
    missing = [k for k in C2_KEYS if k not in table.columns]
    if missing:
        raise ValueError(f"C2 predictions are missing keys: {missing}")
    for col in ("issued_at", "target_start", "target_end"):
        table[col] = pd.to_datetime(table[col])
    return table


def usable_c2_predictions(table: pd.DataFrame, variable: str) -> pd.DataFrame:
    """Only 'valid' predictions for one variable (the contract also defines
    provisional, stale and unavailable, which C3 must not plan on)."""
    return table[(table["status"] == "valid") & (table["variable"] == variable)].reset_index(drop=True)
