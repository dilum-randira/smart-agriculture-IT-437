"""Tests for app/c3/weather_sources.py. No internet: a fake response is used.

The fake values copy the structure of a real Open-Meteo reply (checked
2026-10-21); the numbers are test inputs, not weather data.
"""

import pytest

from app.c3 import optimiser as opt
from app.c3 import weather_sources as ws

FAKE_JSON = {
    "daily": {
        "time": ["2025-05-01", "2025-05-02", "2025-05-03"],
        "temperature_2m_max": [31.6, 31.7, 32.0],
        "temperature_2m_min": [23.1, 24.3, 24.0],
        "relative_humidity_2m_max": [96, 91, 90],
        "relative_humidity_2m_min": [64, 64, 60],
        "relative_humidity_2m_mean": [82, 82, 78],
        "precipitation_sum": [0.4, 3.0, 0.0],
        "wind_speed_10m_mean": [3.72, 2.98, 3.0],
        "shortwave_radiation_sum": [23.58, 21.92, 22.0],
        "et0_fao_evapotranspiration": [5.02, 4.69, 4.8],
    }
}


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def fake_get(url, params=None, timeout=None):
    fake_get.last_call = (url, params)
    return FakeResponse(FAKE_JSON)


def test_request_params_ask_for_m_per_s_and_all_variables():
    params = ws.request_params(7.9, 80.7, forecast_days=8)
    assert params["wind_speed_unit"] == "ms"
    assert params["daily"].split(",") == ws.DAILY_VARIABLES
    assert params["forecast_days"] == 8


def test_parse_open_meteo_daily_renames_and_converts_wind():
    table = ws.parse_open_meteo_daily(FAKE_JSON)
    for col in ("date", "tmax_c", "tmin_c", "rh_max_pct", "rh_min_pct", "rh_mean_pct",
                "rainfall_mm", "wind_speed_2m_ms", "solar_radiation_mj_m2_day"):
        assert col in table.columns
    # FAO-56 Eq. 47: 10 m -> 2 m multiplies by about 0.748
    assert table["wind_speed_2m_ms"].iloc[0] == pytest.approx(3.72 * 0.748, abs=0.01)


def test_parse_open_meteo_daily_rejects_incomplete_response():
    with pytest.raises(ValueError, match="no daily"):
        ws.parse_open_meteo_daily({})
    partial = {"daily": {"time": ["2025-05-01"], "temperature_2m_max": [30.0]}}
    with pytest.raises(ValueError, match="missing daily variables"):
        ws.parse_open_meteo_daily(partial)


def test_fetch_forecast_and_history_use_the_right_urls():
    ws.fetch_forecast(7.9, 80.7, get=fake_get)
    assert fake_get.last_call[0] == ws.FORECAST_URL
    table = ws.fetch_history(7.9, 80.7, "2025-05-01", "2025-05-03", get=fake_get)
    assert fake_get.last_call[0] == ws.ARCHIVE_URL
    assert fake_get.last_call[1]["start_date"] == "2025-05-01"
    assert len(table) == 3


def test_to_c3_forecasts_works_with_the_optimiser():
    daily = ws.parse_open_meteo_daily(FAKE_JSON)
    forecasts = ws.to_c3_forecasts(daily, "2025-05-01")
    assert forecasts["lead_day"].tolist() == [1, 2]
    scenarios = opt.forecast_scenarios(forecasts, "2025-05-01", 7.9, 150.0)
    assert len(scenarios[0].et0_mm_day) == 2
    # Our FAO-56 ET0 should be close to Open-Meteo's own FAO ET0 (independent check).
    assert scenarios[0].et0_mm_day[0] == pytest.approx(4.69, abs=0.6)


# --- C2 contract --------------------------------------------------------------
def c2_record(**changes):
    record = {"prediction_id": "p1", "plot_id": "plot-1", "issued_at": "2025-05-01T06:00",
              "target_start": "2025-05-02T00:00", "target_end": "2025-05-03T00:00",
              "variable": "air_temperature", "unit": "degC", "median": 30.0, "lower": None,
              "upper": None, "interval_level": None, "model_version": "m0",
              "data_version": "d0", "status": "valid"}
    record.update(changes)
    return record


def test_parse_c2_predictions_keeps_null_intervals():
    table = ws.parse_c2_predictions([c2_record()])
    assert table["lower"].isna().all()


def test_parse_c2_predictions_rejects_missing_keys():
    bad = c2_record()
    del bad["status"]
    with pytest.raises(ValueError, match="status"):
        ws.parse_c2_predictions([bad])


def test_usable_c2_predictions_filters_status_and_variable():
    table = ws.parse_c2_predictions([c2_record(), c2_record(status="stale"),
                                     c2_record(variable="relative_humidity")])
    usable = ws.usable_c2_predictions(table, "air_temperature")
    assert len(usable) == 1


# --- Previous Runs (past forecasts as issued) --------------------------------
def fake_previous_runs_json(days: int = 2) -> dict:
    """Hourly test values: constant per variable so daily results are easy to check."""
    import pandas as pd
    times = pd.date_range("2025-05-01", periods=24 * days, freq="h").strftime("%Y-%m-%dT%H:%M")
    hourly = {"time": list(times)}
    n = len(times)
    for lead in ws.LEAD_DAYS:
        hourly[f"temperature_2m_previous_day{lead}"] = [20.0 + (i % 24) / 2 for i in range(n)]
        hourly[f"relative_humidity_2m_previous_day{lead}"] = [60.0 + (i % 24) for i in range(n)]
        hourly[f"precipitation_previous_day{lead}"] = [0.5] * n         # 0.5 mm every hour
        hourly[f"wind_speed_10m_previous_day{lead}"] = [3.0] * n
        hourly[f"shortwave_radiation_previous_day{lead}"] = [250.0] * n  # W/m2
    return {"hourly": hourly}


def test_previous_runs_params_ask_for_all_leads():
    params = ws.previous_runs_params(8.1, 80.4, "2025-05-01", "2025-05-02")
    names = params["hourly"].split(",")
    assert len(names) == len(ws.PREVIOUS_RUN_BASES) * 7
    assert "precipitation_previous_day7" in names


def test_parse_previous_runs_builds_daily_values():
    forecasts = ws.parse_previous_runs(fake_previous_runs_json())
    assert sorted(forecasts["lead_day"].unique()) == list(range(1, 8))
    row = forecasts[(forecasts["lead_day"] == 1)].iloc[0]
    assert row["tmax_c"] == pytest.approx(31.5) and row["tmin_c"] == pytest.approx(20.0)
    assert row["rh_max_pct"] == 83.0 and row["rh_min_pct"] == 60.0
    assert row["rainfall_mm"] == pytest.approx(12.0)               # 24 h x 0.5 mm
    assert row["solar_radiation_mj_m2_day"] == pytest.approx(21.6)  # 24 x 250 x 3600 / 1e6
    assert row["wind_speed_2m_ms"] == pytest.approx(3.0 * 0.748, abs=0.01)
    # target 2025-05-01 at lead 3 was issued on 2025-04-28
    lead3 = forecasts[(forecasts["lead_day"] == 3)].iloc[0]
    assert str(lead3["issue_date"].date()) == "2025-04-28"


def test_parse_previous_runs_drops_incomplete_days():
    data = fake_previous_runs_json()
    data["hourly"]["temperature_2m_previous_day1"][30] = None      # a gap on day 2
    forecasts = ws.parse_previous_runs(data)
    assert len(forecasts[forecasts["lead_day"] == 1]) == 1
    assert len(forecasts[forecasts["lead_day"] == 2]) == 2


def test_parse_previous_runs_rejects_bad_response():
    with pytest.raises(ValueError, match="no hourly"):
        ws.parse_previous_runs({})


def test_fetch_previous_runs_uses_the_right_url():
    calls = {}

    def get(url, params=None, timeout=None):
        calls["url"] = url
        return FakeResponse(fake_previous_runs_json())
    forecasts = ws.fetch_previous_runs(8.1, 80.4, "2025-05-01", "2025-05-02", get=get)
    assert calls["url"] == ws.PREVIOUS_RUNS_URL
    assert len(forecasts) == 2 * 7
