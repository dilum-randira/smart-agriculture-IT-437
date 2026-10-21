"""Tests for app/c3/growth_stages.py. Stage lengths here are test numbers
(FAO-56 Example 28 dry bean: 25/25/30/20), not Nai Miris values."""

import pytest

from app.c3 import growth_stages as gs

LENGTHS = {"initial": 25, "development": 25, "mid": 30, "late": 20}


def test_growth_stage_for_day_boundaries():
    assert gs.growth_stage_for_day(1, 25, 25, 30, 20) == "initial"
    assert gs.growth_stage_for_day(25, 25, 25, 30, 20) == "initial"
    assert gs.growth_stage_for_day(26, 25, 25, 30, 20) == "development"
    assert gs.growth_stage_for_day(80, 25, 25, 30, 20) == "mid"
    assert gs.growth_stage_for_day(81, 25, 25, 30, 20) == "late"
    assert gs.growth_stage_for_day(200, 25, 25, 30, 20) == "late"


def test_daily_values_by_stage():
    values = {"initial": 1.0, "development": 1.0, "mid": 0.5, "late": 1.0}
    daily = gs.daily_values_by_stage(100, LENGTHS, values)
    assert len(daily) == 100
    assert daily[49] == 1.0 and daily[50] == 0.5     # day 50 development, day 51 mid
    assert daily[79] == 0.5 and daily[80] == 1.0     # day 80 mid, day 81 late


def test_daily_values_by_stage_needs_all_stages():
    with pytest.raises(ValueError, match="missing stages"):
        gs.daily_values_by_stage(10, {"initial": 5}, {s: 1.0 for s in gs.STAGES})
