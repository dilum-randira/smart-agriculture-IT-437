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
    # 2 reference rules + 6 DoA variants + 3 optimiser settings
    assert len(table) == 2 + 6 + 3
