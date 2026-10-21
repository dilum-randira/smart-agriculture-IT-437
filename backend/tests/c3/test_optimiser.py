"""Tests for app/c3/optimiser.py (Stage 9 prototype).

These check that the optimiser behaves sensibly. They do NOT show that its
schedules are better than the baselines; that is Stage 11 (evaluation).
"""

import pandas as pd
import pytest

from app.c3 import baselines as bl
from app.c3 import config
from app.c3 import data_loading as dl
from app.c3 import optimiser as opt

DRY = opt.WeatherScenario("dry", et0_mm_day=[5.0] * 7, rain_mm=[0.0] * 7)
KC = [1.2] * 7


# --- relative_et_deficit ----------------------------------------------------
def test_relative_et_deficit():
    assert opt.relative_et_deficit(10.0, 10.0) == 0.0     # no stress
    assert opt.relative_et_deficit(5.0, 10.0) == 0.5      # half the water need met
    assert opt.relative_et_deficit(0.0, 0.0) == 0.0       # no demand -> no deficit


# --- run_schedule -----------------------------------------------------------
def test_run_schedule_matches_baseline_simulator():
    # Same plan through both simulators must give the same crop water use.
    plan = [0.0, 30.0, 0.0, 0.0, 20.0, 0.0, 0.0]
    fast = opt.run_schedule(plan, 40.0, DRY, KC, taw_mm=100.0, raw_mm=40.0)
    slow = bl.simulate_with_rule(lambda day, dep: plan[day - 1], 40.0,
                                 DRY.et0_mm_day, KC, DRY.rain_mm, 100.0, 40.0)
    assert fast["eta_mm"] == pytest.approx(slow["etc_adj_mm"].sum())
    assert fast["deep_percolation_mm"] == pytest.approx(slow["deep_percolation_mm"].sum())


def test_run_schedule_no_stress_when_soil_stays_full():
    # Start at field capacity and give back exactly what the crop uses (6 mm/day).
    result = opt.run_schedule([6.0] * 7, 0.0, DRY, KC, taw_mm=100.0, raw_mm=40.0)
    assert result["relative_et_deficit"] == pytest.approx(0.0)


# --- evaluate_schedule ------------------------------------------------------
def test_evaluate_uses_worst_scenario_for_deficit():
    wet = opt.WeatherScenario("wet", [5.0] * 7, [20.0] * 7)
    plan = [0.0] * 7
    _, deficit_wet_only, _ = opt.evaluate_schedule(plan, 50.0, [wet], KC, 100.0, 40.0)
    _, deficit_both, _ = opt.evaluate_schedule(plan, 50.0, [wet, DRY], KC, 100.0, 40.0)
    assert deficit_both > deficit_wet_only


def test_evaluate_total_water():
    water, _, _ = opt.evaluate_schedule([1, 2, 3, 0, 0, 0, 4], 0.0, [DRY], KC, 100.0, 40.0)
    assert water == 10.0


# --- optimise_schedule ------------------------------------------------------
@pytest.fixture(scope="module")
def front() -> pd.DataFrame:
    return opt.optimise_schedule(50.0, [DRY], KC, taw_mm=100.0, raw_mm=40.0,
                                 pop_size=30, n_generations=40, seed=1)


def test_front_has_one_column_per_day_and_valid_values(front):
    for d in range(1, 8):
        assert f"day{d}_mm" in front.columns
    day_cols = [f"day{d}_mm" for d in range(1, 8)]
    assert (front[day_cols] >= 0).all().all()
    assert (front[day_cols] <= 100.0).all().all()       # upper bound = TAW
    assert front["relative_et_deficit"].between(0, 1).all()


def test_front_shows_the_trade_off(front):
    # More water should buy a smaller deficit across the front.
    least_water = front.iloc[0]
    most_water = front.iloc[-1]
    assert most_water.total_water_mm > least_water.total_water_mm
    assert most_water.relative_et_deficit < least_water.relative_et_deficit


def test_optimiser_is_repeatable_with_same_seed(front):
    again = opt.optimise_schedule(50.0, [DRY], KC, taw_mm=100.0, raw_mm=40.0,
                                  pop_size=30, n_generations=40, seed=1)
    pd.testing.assert_frame_equal(front, again)


def test_optimise_rejects_wrong_scenario_length():
    short = opt.WeatherScenario("short", [5.0] * 3, [0.0] * 3)
    with pytest.raises(ValueError, match="short"):
        opt.optimise_schedule(0.0, [short], KC, 100.0, 40.0, pop_size=10, n_generations=2)


# --- least_water_schedule ---------------------------------------------------
def test_least_water_schedule_picks_cheapest_allowed():
    front = pd.DataFrame({"total_water_mm": [10.0, 20.0, 30.0],
                          "relative_et_deficit": [0.30, 0.10, 0.00]})
    assert opt.least_water_schedule(front, 0.15).total_water_mm == 20.0
    assert opt.least_water_schedule(front, 0.50).total_water_mm == 10.0
    with pytest.raises(ValueError):
        opt.least_water_schedule(front, -0.1)


# --- forecast_scenarios -----------------------------------------------------
def test_forecast_scenarios_from_synthetic_c2_file():
    forecasts = dl.load_forecasts(config.SAMPLE_DATA_DIR / "c2_forecast_synthetic_7day.csv")
    scenarios = opt.forecast_scenarios(forecasts, "2025-06-01", latitude_deg=7.9,
                                       elevation_m=150.0)
    assert [s.name for s in scenarios] == ["forecast", "no_rain"]
    for s in scenarios:
        assert len(s.et0_mm_day) == 7 and all(v > 0 for v in s.et0_mm_day)
    assert scenarios[1].rain_mm == [0.0] * 7


def test_forecast_scenarios_unknown_date():
    forecasts = dl.load_forecasts(config.SAMPLE_DATA_DIR / "c2_forecast_synthetic_7day.csv")
    with pytest.raises(ValueError, match="no forecast"):
        opt.forecast_scenarios(forecasts, "1999-01-01", 7.9, 150.0)
