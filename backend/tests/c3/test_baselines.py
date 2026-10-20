"""Tests for app/c3/baselines.py (Stage 8, part 1).

Uses FAO-56 Examples 37 and 38 (Allen et al., 1998, chapter 8) where
possible, and small hand-checkable cases otherwise.
"""

import pytest

from app.c3 import baselines as bl


# --- rules ------------------------------------------------------------------
def test_no_irrigation_rule_never_irrigates():
    assert bl.no_irrigation_rule(1, 0.0) == 0.0
    assert bl.no_irrigation_rule(30, 150.0) == 0.0


def test_fixed_threshold_rule():
    rule = bl.fixed_threshold_rule(raw_mm=40.0)
    assert rule(1, 39.9) == 0.0          # below RAW: wait
    assert rule(1, 40.0) == 40.0         # at RAW: refill exactly the depletion
    assert rule(1, 55.0) == 55.0


def test_doa_irrigation_days():
    # Every 4 days until day 10, then weekly: 4, 8, 12 (8 < 10), then 12 + 7 = 19.
    days = bl.doa_irrigation_days(season_days=20, interval_early_days=4,
                                  interval_late_days=7, early_stage_end_day=10)
    assert days == [4, 8, 12, 19]


def test_doa_schedule_rule_irrigates_only_on_schedule():
    rule = bl.doa_schedule_rule([4, 8])
    assert rule(4, 30.0) == 30.0
    assert rule(5, 30.0) == 0.0


# --- simulate_with_rule -----------------------------------------------------
def test_simulation_without_irrigation_matches_example_37():
    days = 10
    result = bl.simulate_with_rule(
        bl.no_irrigation_rule, start_depletion_mm=55.0, et0_mm_day=[5.0] * days,
        kc=[1.2] * days, rain_mm=[0.0] * days, taw_mm=160.0, raw_mm=64.0,
    )
    assert result["ks"].iloc[9] == pytest.approx(0.62, abs=0.005)
    assert result["depletion_end_mm"].iloc[9] == pytest.approx(104.5, abs=0.1)


def test_fixed_threshold_matches_example_38_day_10():
    # Example 38, day 10: depletion = RAW = 27 mm, ET0 5.2, Kc 1.21.
    # FAO-56: 27 mm irrigation, Ks 1, ETc 6.3 mm, no deep percolation, Dr end 6 mm.
    result = bl.simulate_with_rule(
        bl.fixed_threshold_rule(raw_mm=27.0), start_depletion_mm=27.0,
        et0_mm_day=[5.2], kc=[1.21], rain_mm=[0.0], taw_mm=100.0, raw_mm=27.0,
    )
    day = result.iloc[0]
    assert day.irrigation_mm == pytest.approx(27.0)
    assert day.ks == 1.0
    assert day.etc_adj_mm == pytest.approx(6.3, abs=0.05)
    assert day.deep_percolation_mm == 0.0
    assert day.depletion_end_mm == pytest.approx(6.3, abs=0.05)


def test_fixed_threshold_keeps_crop_unstressed():
    days = 30
    result = bl.simulate_with_rule(
        bl.fixed_threshold_rule(raw_mm=64.0), start_depletion_mm=0.0,
        et0_mm_day=[5.0] * days, kc=[1.2] * days, rain_mm=[0.0] * days,
        taw_mm=160.0, raw_mm=64.0,
    )
    assert (result["ks"] == 1.0).all()
    assert (result["irrigation_mm"] > 0).sum() >= 1


def test_simulation_rejects_lists_of_different_lengths():
    with pytest.raises(ValueError, match="kc"):
        bl.simulate_with_rule(bl.no_irrigation_rule, 0.0, [5.0, 5.0], [1.0], [0.0, 0.0],
                              100.0, 40.0)


# --- summarise_schedule -----------------------------------------------------
def test_summarise_schedule():
    result = bl.simulate_with_rule(
        bl.doa_schedule_rule([2]), start_depletion_mm=70.0, et0_mm_day=[5.0, 5.0, 5.0],
        kc=[1.0, 1.0, 1.0], rain_mm=[0.0, 0.0, 0.0], taw_mm=100.0, raw_mm=50.0,
    )
    summary = bl.summarise_schedule(result)
    assert summary["irrigation_events"] == 1
    assert summary["stress_days"] == 1                 # day 1 starts at 70 mm > RAW
    assert summary["total_irrigation_mm"] == pytest.approx(result["irrigation_mm"].sum())
    assert 0.0 < summary["mean_ks"] < 1.0
