"""Tests for app/c3/evaluation.py and the synthetic evaluation script (Stage 11).

Short seasons and small NSGA-II settings keep these fast. They check the
pipeline works, not which schedule is best.
"""

import pandas as pd
import pytest

from app.c3 import baselines as bl
from app.c3 import config
from app.c3 import data_loading as dl
from app.c3 import evaluation as ev
from app.c3.scripts import run_synthetic_evaluation as script

SAMPLE = config.SAMPLE_DATA_DIR
LAT, ELEV = 7.9, 150.0
TAW, RAW = 60.0, 18.0
DAYS = 10


@pytest.fixture(scope="module")
def truth() -> pd.DataFrame:
    weather = dl.load_weather(SAMPLE / "weather_synthetic_daily.csv")
    return ev.season_truth(weather, "2025-05-01", DAYS, LAT, ELEV)


# --- season_truth -----------------------------------------------------------
def test_season_truth_has_et0_and_tmean(truth):
    assert len(truth) == DAYS
    assert (truth["et0_mm_day"] > 0).all()
    assert truth["tmean_c"].iloc[0] == pytest.approx((truth.tmax_c[0] + truth.tmin_c[0]) / 2)


def test_season_truth_rejects_dates_outside_the_file():
    weather = dl.load_weather(SAMPLE / "weather_synthetic_daily.csv")
    with pytest.raises(ValueError, match="weather covers"):
        ev.season_truth(weather, "2025-12-25", 30, LAT, ELEV)


# --- optimiser_rule ---------------------------------------------------------
def test_optimiser_rule_returns_a_valid_amount(truth):
    forecasts = dl.load_forecasts(SAMPLE / "c2_forecast_synthetic_7day.csv")
    rule = ev.optimiser_rule(forecasts, truth["date"].tolist(), [1.05] * DAYS, TAW, RAW,
                             LAT, ELEV, max_relative_et_deficit=0.0,
                             pop_size=10, n_generations=5)
    amount = rule(1, 30.0)
    assert 0.0 <= amount <= TAW


def test_optimiser_rule_irrigates_when_crop_would_be_stressed(truth):
    # Depletion 30 mm is beyond RAW (18 mm): a zero-deficit plan must refill today.
    forecasts = dl.load_forecasts(SAMPLE / "c2_forecast_synthetic_7day.csv")
    rule = ev.optimiser_rule(forecasts, truth["date"].tolist(), [1.05] * DAYS, TAW, RAW,
                             LAT, ELEV, max_relative_et_deficit=0.0)
    assert rule(1, 30.0) == pytest.approx(30.0)


def test_script_optimiser_rows_irrigate(tmp_path):
    # Guards against settings being passed into the wrong parameter.
    table = script.main(season_days=DAYS, output_dir=tmp_path)
    optimiser_rows = table[table["schedule"].str.startswith("NSGA-II")]
    assert (optimiser_rows["total_irrigation_mm"] > 0).all()


# --- run_season -------------------------------------------------------------
def test_fixed_threshold_season_has_no_stress(truth):
    result = ev.run_season(bl.fixed_threshold_rule(RAW), truth, [1.05] * DAYS, TAW, RAW)
    assert len(result) == DAYS
    assert (result["ks"] == 1.0).all()


# --- compare_schedules ------------------------------------------------------
def test_compare_schedules_one_row_per_schedule(truth):
    kc = [1.05] * DAYS
    results = {
        "none": ev.run_season(bl.no_irrigation_rule, truth, kc, TAW, RAW),
        "fixed": ev.run_season(bl.fixed_threshold_rule(RAW), truth, kc, TAW, RAW),
    }
    table = ev.compare_schedules(results, truth, kc)
    assert table["schedule"].tolist() == ["none", "fixed"]
    for col in ("total_irrigation_mm", "relative_et_deficit", "heat_risk_days",
                "drought_risk_days", "longest_wet_run_days", "root_rot_risk_days"):
        assert col in table.columns
    none, fixed = table.iloc[0], table.iloc[1]
    assert none.total_irrigation_mm == 0.0
    assert none.relative_et_deficit >= fixed.relative_et_deficit


# --- script -----------------------------------------------------------------
def test_script_runs_and_saves_a_synthetic_file(tmp_path):
    table = script.main(season_days=DAYS, pop_size=10, n_generations=5, output_dir=tmp_path)
    assert (tmp_path / "evaluation_synthetic.csv").exists()
    # 2 reference rules + 6 DoA variants + reactive ML + 3 optimiser settings
    assert len(table) == 2 + 6 + 1 + 3


# --- perfect forecasts --------------------------------------------------------
def test_perfect_forecasts_copy_the_true_weather(truth):
    table = ev.perfect_forecasts(truth, horizon=3)
    assert sorted(table["lead_day"].unique()) == [1, 2, 3]
    row = table[(table["lead_day"] == 2)].iloc[0]
    true_day = truth[truth["date"] == row["target_date"]].iloc[0]
    assert row["tmax_c"] == true_day["tmax_c"]
    assert (row["target_date"] - row["issue_date"]).days == 2


# --- real-weather script, offline (downloads replaced by SYNTHETIC test data) --
def test_real_weather_script_runs_offline(tmp_path, monkeypatch):
    from app.c3 import weather_sources as ws
    from app.c3.scripts import run_real_weather_evaluation as real
    sample = dl.load_weather(SAMPLE / "weather_synthetic_daily.csv")

    def history(lat, lon, start, end, get=None):
        return sample[(sample["date"] >= start) & (sample["date"] <= end)].reset_index(drop=True)

    def previous_runs(lat, lon, start, end, get=None):
        return ev.perfect_forecasts(history(lat, lon, start, end))

    monkeypatch.setattr(ws, "fetch_history", history)
    monkeypatch.setattr(ws, "fetch_previous_runs", previous_runs)
    table = real.main(season_start="2025-05-01", season_days=5, pop_size=10, n_generations=5,
                      data_dir=tmp_path / "data", output_dir=tmp_path / "out")
    # 2 reference + 6 DoA + reactive ML + 3 NSGA-II + 1 perfect-forecast NSGA-II
    assert len(table) == 13
    assert (tmp_path / "out" / "evaluation_real_weather_demo_location.csv").exists()
    assert len(list((tmp_path / "data").glob("*.csv"))) == 3     # downloads cached


def test_optimiser_rule_can_trust_the_forecast(truth):
    # With a big rain in the forecast, trusting it (no "rain fails" case) may
    # wait; the worst-case version must protect the crop. Both stay valid.
    forecasts = dl.load_forecasts(SAMPLE / "c2_forecast_synthetic_7day.csv")
    common = (forecasts, truth["date"].tolist(), [1.05] * DAYS, TAW, RAW, LAT, ELEV, 0.0)
    trusting = ev.optimiser_rule(*common, worst_case_no_rain=False, pop_size=10, n_generations=5)
    careful = ev.optimiser_rule(*common, worst_case_no_rain=True, pop_size=10, n_generations=5)
    for rule in (trusting, careful):
        assert 0.0 <= rule(1, 10.0) <= TAW
