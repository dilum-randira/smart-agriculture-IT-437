"""Tests for each function in app/c3/scripts/generate_synthetic_data.py.

These test the GENERATOR CODE. test_synthetic_data.py tests the saved files.
Everything here is synthetic; nothing is a research result.
"""

import json

import numpy as np
import pandas as pd
import pytest

from app.c3 import config
from app.c3.scripts import generate_synthetic_data as gen


@pytest.fixture(scope="module")
def weather() -> pd.DataFrame:
    """Synthetic daily weather, made once and shared by the tests below."""
    return gen.make_daily_weather(np.random.default_rng(gen.SEED))


# --- extraterrestrial_radiation ---------------------------------------------
def test_radiation_is_positive():
    for day in (1, 100, 200, 300, 365):
        assert gen.extraterrestrial_radiation(day, gen.LATITUDE_DEG) > 0


def test_radiation_is_higher_in_local_summer():
    # Basic astronomy: at 45 deg the summer solstice gets more radiation than
    # the winter solstice. Day 172 = 21 June, day 355 = 21 December.
    assert gen.extraterrestrial_radiation(172, 45.0) > gen.extraterrestrial_radiation(355, 45.0)
    assert gen.extraterrestrial_radiation(355, -45.0) > gen.extraterrestrial_radiation(172, -45.0)


# --- seasonal ---------------------------------------------------------------
def test_seasonal_picks_the_right_month():
    months = list(range(1, 13))
    assert gen.seasonal(1, months) == 1    # January is the first item
    assert gen.seasonal(12, months) == 12  # December is the last item


# --- make_daily_weather -----------------------------------------------------
def test_weather_has_one_row_per_day(weather):
    assert len(weather) == 731  # 2024 (leap year, 366 days) + 2025 (365 days)


def test_weather_values_stay_in_generator_limits(weather):
    assert (weather.tmin_c <= weather.tmax_c - 4.0 + 0.1).all()  # +0.1 for rounding
    assert weather.rh_mean_pct.between(40, 98).all()
    assert (weather.rainfall_mm >= 0).all()
    assert (weather.wind_speed_2m_ms >= 0.3).all()


def test_weather_is_repeatable_with_same_seed(weather):
    again = gen.make_daily_weather(np.random.default_rng(gen.SEED))
    pd.testing.assert_frame_equal(weather, again)


# --- make_sensor_stream -----------------------------------------------------
def test_sensor_stream_shape_and_faults(weather):
    plot = gen.make_plot_config()
    sensors = gen.make_sensor_stream(weather, plot, np.random.default_rng(gen.SEED))
    assert len(sensors) == gen.SENSOR_DAYS * 96            # 96 readings per day
    assert sensors.soil_moisture_pct.isna().any()           # outages added
    assert (sensors.soil_moisture_pct > 100).any()          # impossible spikes added
    assert (sensors.light_lux.dropna() <= 65535).all()      # BH1750 maximum
    assert (sensors.irrigation_logged_mm >= 0).all()


# --- make_forecasts ---------------------------------------------------------
def test_forecasts_lead_days_match_dates(weather):
    forecasts = gen.make_forecasts(weather, np.random.default_rng(gen.SEED))
    assert len(forecasts) == (len(weather) - 7) * 7
    days_ahead = (pd.to_datetime(forecasts.target_date) - pd.to_datetime(forecasts.issue_date)).dt.days
    assert (days_ahead == forecasts.lead_day).all()
    assert (forecasts.tmax_c_p10 <= forecasts.tmax_c).all()
    assert (forecasts.tmax_c <= forecasts.tmax_c_p90).all()
    assert (forecasts.rainfall_mm >= 0).all()


# --- make_plot_config -------------------------------------------------------
def test_plot_config_is_placeholder_and_consistent():
    plot = gen.make_plot_config()
    assert "PLACEHOLDER" in plot["_status"]
    assert plot["soil"]["wilting_point_m3m3"] < plot["soil"]["field_capacity_m3m3"]
    assert plot["plot"]["water_cost_lkr_per_m3"] is None  # unknown on purpose


# --- main -------------------------------------------------------------------
def test_main_recreates_the_committed_sample_files(tmp_path, monkeypatch):
    # Write to a temporary folder so the real sample/ folder is not touched.
    monkeypatch.setattr(gen, "OUT", tmp_path)
    gen.main()
    for name in ("weather_synthetic_daily.csv",
                 "c1_sensor_synthetic_15min.csv",
                 "c2_forecast_synthetic_7day.csv"):
        new = pd.read_csv(tmp_path / name)
        committed = pd.read_csv(config.SAMPLE_DATA_DIR / name)
        pd.testing.assert_frame_equal(new, committed)
    with open(tmp_path / "plot_soil_config_synthetic.json", encoding="utf-8") as f:
        new_plot = json.load(f)
    with open(config.SAMPLE_DATA_DIR / "plot_soil_config_synthetic.json", encoding="utf-8") as f:
        assert new_plot == json.load(f)
