"""Tests for app/c3/optimiser.py (Stage 9, version 2).

These check that the optimiser behaves correctly. They do NOT show that its
schedules are better than the baselines; that is Stage 11 (evaluation).
"""

import pandas as pd
import pytest

from app.c3 import baselines as bl
from app.c3 import config
from app.c3 import data_loading as dl
from app.c3 import optimiser as opt

DRY = opt.WeatherScenario("dry", [5.0] * 7, [0.0] * 7, [28.0] * 7)
KC = [1.2] * 7
TAW, RAW = 100.0, 40.0


# --- relative_et_deficit ----------------------------------------------------
def test_relative_et_deficit():
    assert opt.relative_et_deficit(10.0, 10.0) == 0.0
    assert opt.relative_et_deficit(5.0, 10.0) == 0.5
    assert opt.relative_et_deficit(0.0, 0.0) == 0.0


# --- run_schedule -----------------------------------------------------------
def test_run_schedule_matches_baseline_simulator():
    plan = [False, True, False, False, True, False, False]
    fast = opt.run_schedule(plan, 40.0, DRY, KC, TAW, RAW)
    slow = bl.simulate_with_rule(lambda day, dep: dep if plan[day - 1] else 0.0, 40.0,
                                 DRY.et0_mm_day, KC, DRY.rain_mm, TAW, RAW)
    assert fast["total_water_mm"] == pytest.approx(slow["irrigation_mm"].sum())
    assert fast["irrigation_events"] == 2
    assert fast["deep_percolation_mm"] == pytest.approx(slow["deep_percolation_mm"].sum())


def test_run_schedule_refills_to_field_capacity():
    # Start 30 mm depleted and irrigate on day 1: exactly 30 mm applied, no drainage.
    result = opt.run_schedule([True] + [False] * 6, 30.0, DRY, KC, TAW, RAW)
    assert result["total_water_mm"] == pytest.approx(30.0)
    assert result["deep_percolation_mm"] == 0.0


def test_run_schedule_skips_irrigation_below_minimum():
    # Only 3 mm needed but the minimum practical amount is 5 mm: no irrigation.
    result = opt.run_schedule([True] + [False] * 6, 3.0, DRY, KC, TAW, RAW,
                              min_irrigation_mm=5.0)
    assert result["total_water_mm"] == 0.0 and result["irrigation_events"] == 0


def test_run_schedule_counts_root_rot_days():
    wet_warm = opt.WeatherScenario("wet", [5.0] * 7, [30.0] * 7, [28.0] * 7)
    result = opt.run_schedule([False] * 7, 0.0, wet_warm, KC, TAW, RAW)
    assert result["root_rot_risk_days"] == 7      # drains every day, Tmean 28 degC


# --- evaluate_schedule ------------------------------------------------------
def test_evaluate_uses_worst_scenario_for_deficit():
    wet = opt.WeatherScenario("wet", [5.0] * 7, [20.0] * 7, [28.0] * 7)
    plan = [False] * 7
    wet_only = opt.evaluate_schedule(plan, 50.0, [wet], KC, TAW, RAW)
    both = opt.evaluate_schedule(plan, 50.0, [wet, DRY], KC, TAW, RAW)
    assert both[1] > wet_only[1]


# --- all_schedules / pareto_front -------------------------------------------
@pytest.fixture(scope="module")
def exact_front() -> pd.DataFrame:
    return opt.pareto_front(opt.all_schedules(50.0, [DRY], KC, TAW, RAW))


def test_all_schedules_lists_every_plan():
    three_days = opt.WeatherScenario("d3", [5.0] * 3, [0.0] * 3, [28.0] * 3)
    table = opt.all_schedules(50.0, [three_days], [1.2] * 3, TAW, RAW)
    assert len(table) == 2 ** 3


def test_pareto_front_removes_dominated_rows():
    table = pd.DataFrame({"total_water_mm": [10, 10, 20], "relative_et_deficit": [0.1, 0.2, 0.0],
                          "irrigation_events": [1, 1, 2], "root_rot_risk_days": [0, 0, 0]})
    front = opt.pareto_front(table)
    assert front["relative_et_deficit"].tolist() == [0.1, 0.0]   # the 0.2 row is dominated


def test_nsga2_finds_the_exact_front(exact_front):
    found = opt.optimise_schedule(50.0, [DRY], KC, TAW, RAW)
    found_front = opt.pareto_front(found)
    key = lambda df: set(map(tuple, df[opt.OBJECTIVES].round(9).to_numpy()))
    assert key(exact_front) <= key(found_front)


def test_optimiser_is_repeatable_with_same_seed():
    a = opt.optimise_schedule(50.0, [DRY], KC, TAW, RAW, seed=3)
    b = opt.optimise_schedule(50.0, [DRY], KC, TAW, RAW, seed=3)
    pd.testing.assert_frame_equal(a, b)


def test_optimise_rejects_wrong_scenario_length():
    short = opt.WeatherScenario("short", [5.0] * 3, [0.0] * 3, [28.0] * 3)
    with pytest.raises(ValueError, match="short"):
        opt.optimise_schedule(0.0, [short], KC, TAW, RAW, pop_size=10, n_generations=2)


# --- least_water_schedule ---------------------------------------------------
def test_least_water_schedule_picks_cheapest_allowed_then_fewest_events():
    front = pd.DataFrame({"total_water_mm": [10.0, 20.0, 20.0, 30.0],
                          "relative_et_deficit": [0.30, 0.10, 0.10, 0.00],
                          "irrigation_events": [1, 3, 2, 2],
                          "root_rot_risk_days": [0, 0, 0, 0]})
    choice = opt.least_water_schedule(front, 0.15)
    assert choice.total_water_mm == 20.0 and choice.irrigation_events == 2
    assert opt.least_water_schedule(front, 0.50).total_water_mm == 10.0
    with pytest.raises(ValueError):
        opt.least_water_schedule(front, -0.1)


# --- forecast_scenarios -----------------------------------------------------
def test_forecast_scenarios_from_synthetic_c2_file():
    forecasts = dl.load_forecasts(config.SAMPLE_DATA_DIR / "c2_forecast_synthetic_7day.csv")
    scenarios = opt.forecast_scenarios(forecasts, "2025-06-01", 7.9, 150.0)
    assert [s.name for s in scenarios] == ["forecast", "no_rain"]
    for s in scenarios:
        assert len(s.et0_mm_day) == len(s.tmean_c) == 7
        assert all(v > 0 for v in s.et0_mm_day)
    assert scenarios[1].rain_mm == [0.0] * 7


def test_forecast_scenarios_unknown_date():
    forecasts = dl.load_forecasts(config.SAMPLE_DATA_DIR / "c2_forecast_synthetic_7day.csv")
    with pytest.raises(ValueError, match="no forecast"):
        opt.forecast_scenarios(forecasts, "1999-01-01", 7.9, 150.0)
