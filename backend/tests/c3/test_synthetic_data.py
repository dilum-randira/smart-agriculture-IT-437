"""Checks that the synthetic sample files exist and have sensible shapes.

These test the FILES, not any C3 calculation.
"""

import json

import pandas as pd

from app.c3 import config

SAMPLE = config.SAMPLE_DATA_DIR


def test_all_sample_files_are_named_synthetic():
    for path in SAMPLE.glob("*.csv"):
        assert "synthetic" in path.name
    for path in SAMPLE.glob("*.json"):
        assert "synthetic" in path.name


def test_weather_columns_and_ranges():
    weather = pd.read_csv(SAMPLE / "weather_synthetic_daily.csv")
    expected = {"date", "tmax_c", "tmin_c", "rh_mean_pct", "rainfall_mm",
                "wind_speed_2m_ms", "solar_radiation_mj_m2_day"}
    assert expected <= set(weather.columns)
    assert (weather.tmin_c < weather.tmax_c).all()
    assert weather.rh_mean_pct.between(0, 100).all()
    assert (weather.rainfall_mm >= 0).all()


def test_forecasts_have_seven_lead_days():
    forecasts = pd.read_csv(SAMPLE / "c2_forecast_synthetic_7day.csv")
    assert sorted(forecasts.lead_day.unique()) == [1, 2, 3, 4, 5, 6, 7]


def test_sensor_file_contains_faults_on_purpose():
    sensors = pd.read_csv(SAMPLE / "c1_sensor_synthetic_15min.csv")
    assert sensors.soil_moisture_pct.isna().any()          # outages
    assert (sensors.soil_moisture_pct > 100).any()         # impossible spikes


def test_plot_config_is_marked_placeholder():
    with open(SAMPLE / "plot_soil_config_synthetic.json", encoding="utf-8") as f:
        plot = json.load(f)
    assert "PLACEHOLDER" in plot["_status"].upper()
    soil = plot["soil"]
    assert soil["wilting_point_m3m3"] < soil["field_capacity_m3m3"]
