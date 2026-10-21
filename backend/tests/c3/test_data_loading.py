"""Tests for app/c3/data_loading.py (Stage 2).

The loader tests use the SYNTHETIC sample files. The helper tests use tiny
hand-made tables so the expected answers are easy to check by eye.
"""

import json

import numpy as np
import pandas as pd
import pytest

from app.c3 import config
from app.c3 import data_loading as dl

SAMPLE = config.SAMPLE_DATA_DIR


# --- check_required_columns -------------------------------------------------
def test_check_required_columns_passes_when_all_present():
    df = pd.DataFrame({"a": [1], "b": [2]})
    dl.check_required_columns(df, ["a", "b"], "test.csv")  # no error


def test_check_required_columns_names_the_missing_column():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="'b'"):
        dl.check_required_columns(df, ["a", "b"], "test.csv")


# --- count_missing_values ---------------------------------------------------
def test_count_missing_values():
    df = pd.DataFrame({"a": [1.0, np.nan, np.nan], "b": [1.0, 2.0, 3.0]})
    assert dl.count_missing_values(df) == {"a": 2}  # 'b' has none, so not listed


# --- find_out_of_range / blank_out_of_range ---------------------------------
def test_find_out_of_range_checks_both_limits_and_ignores_blanks():
    df = pd.DataFrame({"x": [-1.0, 50.0, 150.0, np.nan]})
    mask = dl.find_out_of_range(df, {"x": (0.0, 100.0)})
    assert mask["x"].tolist() == [True, False, True, False]


def test_find_out_of_range_with_no_upper_limit():
    df = pd.DataFrame({"rain": [-0.1, 0.0, 500.0]})
    mask = dl.find_out_of_range(df, {"rain": (0.0, None)})
    assert mask["rain"].tolist() == [True, False, False]


def test_blank_out_of_range_replaces_bad_values_and_keeps_input():
    df = pd.DataFrame({"x": [-1.0, 50.0, 150.0]})
    cleaned, counts = dl.blank_out_of_range(df, {"x": (0.0, 100.0)})
    assert cleaned["x"].isna().tolist() == [True, False, True]
    assert counts == {"x": 2}
    assert df["x"].tolist() == [-1.0, 50.0, 150.0]  # original not changed


# --- loaders ----------------------------------------------------------------
def test_load_weather_parses_dates():
    weather = dl.load_weather(SAMPLE / "weather_synthetic_daily.csv")
    assert pd.api.types.is_datetime64_any_dtype(weather["date"])
    assert len(weather) == 731


def test_load_weather_rejects_file_with_missing_column(tmp_path):
    bad = tmp_path / "bad_weather.csv"
    pd.DataFrame({"date": ["2024-01-01"], "tmax_c": [30.0]}).to_csv(bad, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        dl.load_weather(bad)


def test_load_sensors_parses_timestamps():
    sensors = dl.load_sensors(SAMPLE / "c1_sensor_synthetic_15min.csv")
    assert pd.api.types.is_datetime64_any_dtype(sensors["timestamp"])
    assert len(sensors) == 90 * 96  # 90 days x 96 readings per day


def test_load_forecasts_parses_both_dates():
    forecasts = dl.load_forecasts(SAMPLE / "c2_forecast_synthetic_7day.csv")
    assert pd.api.types.is_datetime64_any_dtype(forecasts["issue_date"])
    assert pd.api.types.is_datetime64_any_dtype(forecasts["target_date"])


def test_load_plot_config_reads_soil():
    plot = dl.load_plot_config(SAMPLE / "plot_soil_config_synthetic.json")
    assert plot["soil"]["field_capacity_m3m3"] == 0.22


def test_load_plot_config_rejects_wilting_point_above_field_capacity(tmp_path):
    bad = tmp_path / "bad_plot.json"
    bad.write_text(json.dumps({"soil": {"field_capacity_m3m3": 0.10,
                                        "wilting_point_m3m3": 0.20}}))
    with pytest.raises(ValueError, match="wilting_point"):
        dl.load_plot_config(bad)


# --- add_soil_moisture_m3m3 -------------------------------------------------
def test_add_soil_moisture_m3m3_divides_by_100():
    df = pd.DataFrame({"soil_moisture_pct": [20.0, np.nan]})
    out = dl.add_soil_moisture_m3m3(df)
    assert out["soil_moisture_m3m3"].iloc[0] == pytest.approx(0.20)
    assert np.isnan(out["soil_moisture_m3m3"].iloc[1])
    assert "soil_moisture_m3m3" not in df.columns  # original not changed


# --- daily_sensor_summary ---------------------------------------------------
def test_daily_sensor_summary_on_two_small_days():
    sensors = pd.DataFrame({
        "timestamp": pd.to_datetime(["2025-05-01 00:00", "2025-05-01 12:00",
                                     "2025-05-02 00:00", "2025-05-02 12:00"]),
        "soil_moisture_pct": [20.0, 22.0, np.nan, 18.0],
        "air_temp_c": [24.0, 32.0, 25.0, 31.0],
        "air_humidity_pct": [80.0, 60.0, 90.0, 70.0],
        "rainfall_mm": [0.0, 2.5, 1.0, 0.0],
        "irrigation_logged_mm": [0.0, 5.0, 0.0, 0.0],
    })
    daily = dl.daily_sensor_summary(sensors)
    assert len(daily) == 2
    day1, day2 = daily.iloc[0], daily.iloc[1]
    assert day1.soil_moisture_mean_pct == 21.0
    assert day1.air_temp_max_c == 32.0 and day1.air_temp_min_c == 24.0
    assert day1.rainfall_mm_day == 2.5 and day1.irrigation_mm_day == 5.0
    assert day2.soil_moisture_mean_pct == 18.0      # the blank is skipped
    assert day2.soil_moisture_readings == 1


# --- whole pipeline on the synthetic sensor file ----------------------------
def test_pipeline_removes_the_impossible_spikes():
    sensors = dl.load_sensors(SAMPLE / "c1_sensor_synthetic_15min.csv")
    cleaned, counts = dl.blank_out_of_range(sensors, dl.SENSOR_LIMITS)
    assert counts.get("soil_moisture_pct", 0) > 0          # the 150 % spikes
    assert (cleaned["soil_moisture_pct"].dropna() <= 100).all()
    daily = dl.daily_sensor_summary(cleaned)
    assert len(daily) == 90


# --- find_spikes ------------------------------------------------------------
def test_find_spikes_flags_up_and_down_spikes():
    values = pd.Series([20.0, 20.5, 150.0, 20.4, 20.3, 0.0, 20.2])
    assert dl.find_spikes(values, max_jump=10.0).tolist() == \
        [False, False, True, False, False, True, False]


def test_find_spikes_ignores_real_step_changes_and_blanks():
    irrigation_step = pd.Series([15.0, 15.1, 25.0, 25.2, 25.1])   # rises and stays
    assert not dl.find_spikes(irrigation_step, max_jump=5.0).any()
    with_blank = pd.Series([20.0, np.nan, 20.0])
    assert not dl.find_spikes(with_blank, max_jump=5.0).any()


def test_find_spikes_catches_synthetic_99_9_and_0_spikes():
    sensors = dl.load_sensors(SAMPLE / "c1_sensor_synthetic_15min.csv")
    spikes = dl.find_spikes(sensors["soil_moisture_pct"], max_jump=10.0)   # test value only
    flagged = sensors.loc[spikes, "soil_moisture_pct"].tolist()
    assert 99.9 in flagged and 0.0 in flagged
