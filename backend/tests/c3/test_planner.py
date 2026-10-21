"""Tests for app/c3/planner.py (Stage 10). Uses the SYNTHETIC forecast file
and test plot values (the synthetic plot config placeholders)."""

import pytest

from app.c3 import config
from app.c3 import data_loading as dl
from app.c3 import optimiser as opt
from app.c3 import planner

PLOT = planner.PlotSettings(latitude_deg=7.9, elevation_m=150.0, field_capacity_m3m3=0.22,
                            wilting_point_m3m3=0.10, root_depth_m=0.5,
                            depletion_fraction_p=0.30, area_m2=50.0)
KC = [1.05] * 7


@pytest.fixture(scope="module")
def forecasts():
    return dl.load_forecasts(config.SAMPLE_DATA_DIR / "c2_forecast_synthetic_7day.csv")


def test_current_depletion_is_clipped_to_0_and_taw():
    assert planner.current_depletion_mm(0.17, PLOT) == pytest.approx(25.0)
    assert planner.current_depletion_mm(0.30, PLOT) == 0.0          # wetter than FC
    assert planner.current_depletion_mm(0.00, PLOT) == pytest.approx(60.0)   # = TAW


def test_plan_today_dry_soil_irrigates_today(forecasts):
    result = planner.plan_today(0.16, forecasts, "2025-06-01", PLOT, KC, 0.0)
    assert result["today"]["date"] == "2025-06-02"
    assert result["today"]["irrigate"] is True
    assert result["today"]["amount_mm"] == pytest.approx(30.0)     # refill 30 mm depletion
    assert result["today"]["volume_m3"] == pytest.approx(1.5)      # 30 mm x 50 m2
    assert len(result["plan"]) == 7
    assert result["meets_allowed_deficit"] is True


def test_plan_today_full_soil_does_not_irrigate_today(forecasts):
    result = planner.plan_today(0.22, forecasts, "2025-06-01", PLOT, KC, 0.0)
    assert result["today"]["irrigate"] is False and result["today"]["amount_mm"] == 0.0


def test_plan_today_adds_cost_and_partial_refill(forecasts):
    result = planner.plan_today(0.16, forecasts, "2025-06-01", PLOT, KC, 0.0,
                                refill_fraction=[0.5] * 7, water_price_lkr_per_m3=100.0)
    assert "cost_lkr" in result["pareto_front"][0]
    if result["today"]["irrigate"]:
        assert result["today"]["amount_mm"] == pytest.approx(15.0)   # 50 % of 30 mm


# --- explanations and week comparison ----------------------------------------

RAINY = opt.WeatherScenario("forecast", [5.0] * 7, [0.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.0], [28.0] * 7)
DATES = [f"2025-06-0{d}" for d in range(2, 9)]


def test_plan_rule_follows_flags_and_refill():
    rule = planner.plan_rule([True, False] + [False] * 5, refill_fraction=[0.5] * 7)
    assert rule(1, 20.0) == pytest.approx(10.0)
    assert rule(2, 20.0) == 0.0


def test_explain_days_states_the_numbers():
    rule = planner.plan_rule([True] + [False] * 6)
    days = planner.explain_days(rule, 25.0, RAINY, KC, 60.0, 18.0, DATES)
    assert len(days) == 7
    assert days[0]["irrigation_mm"] == pytest.approx(25.0)
    assert days[0]["reason"].startswith("Irrigate 25 mm")
    assert "15.0 mm rain forecast" in days[1]["reason"]


def test_compare_week_rows():
    rows = planner.compare_week({"none": planner.plan_rule([False] * 7),
                                 "every day": planner.plan_rule([True] * 7)},
                                25.0, RAINY, KC, 60.0, 18.0)
    assert [r["schedule"] for r in rows] == ["none", "every day"]
    assert rows[0]["water_mm"] == 0.0
    assert rows[0]["relative_et_deficit"] > rows[1]["relative_et_deficit"]


def test_plan_today_includes_explanations_and_comparison(forecasts):
    result = planner.plan_today(0.16, forecasts, "2025-06-01", PLOT, KC, 0.0)
    assert len(result["days"]) == 7 and "reason" in result["days"][0]
    names = [r["schedule"] for r in result["week_comparison"]]
    assert names == ["C3 (uses the forecast)", "C3 ignoring forecast rain",
                     "Fixed threshold (reacts to soil only)"]


def test_plan_tiles_match_the_explained_irrigation(forecasts):
    result = planner.plan_today(0.16, forecasts, "2025-06-01", PLOT, KC, 0.0)
    for tile, day in zip(result["plan"], result["days"]):
        assert tile["irrigate"] == (day["irrigation_mm"] > 0)
        assert tile["amount_mm"] == day["irrigation_mm"]
