"""Tests for app/c3/water_balance.py, checked against FAO-56 worked examples.

Expected values come from FAO Irrigation and Drainage Paper 56 (Allen et al.,
1998): Example 28 (chapter 6) and Examples 36 and 37 (chapter 8).
"""

import pytest

from app.c3 import water_balance as wb

# FAO-56 Example 28 (dry bean): stage lengths 25/25/30/20 days, Kc 0.15/1.19/0.35.
EX28 = dict(l_ini=25, l_dev=25, l_mid=30, l_late=20, kc_ini=0.15, kc_mid=1.19, kc_end=0.35)


# --- kc_for_day -------------------------------------------------------------
def test_kc_example_28_all_four_days():
    assert wb.kc_for_day(20, **EX28) == pytest.approx(0.15)               # initial
    assert wb.kc_for_day(40, **EX28) == pytest.approx(0.77, abs=0.005)    # development
    assert wb.kc_for_day(70, **EX28) == pytest.approx(1.19)               # mid-season
    assert wb.kc_for_day(95, **EX28) == pytest.approx(0.56, abs=0.005)    # late season


def test_kc_stays_at_kc_end_after_the_season():
    assert wb.kc_for_day(150, **EX28) == pytest.approx(0.35)


# --- crop_et_mm_day ---------------------------------------------------------
def test_crop_et_example_37():
    # Example 37: Kc 1.2 and ET0 5 mm/day give ETc 6.0 mm/day.
    assert wb.crop_et_mm_day(1.2, 5.0) == pytest.approx(6.0)


# --- TAW and RAW ------------------------------------------------------------
def test_taw_and_raw_example_37():
    # Silty soil, theta FC 0.32, theta WP 0.12, Zr 0.8 m, p 0.40.
    taw = wb.total_available_water_mm(0.32, 0.12, 0.8)
    assert taw == pytest.approx(160.0)
    assert wb.readily_available_water_mm(taw, 0.40) == pytest.approx(64.0)


def test_raw_example_36_maize():
    # Example 36: maize p 0.55, TAW 108 mm on loamy sand -> RAW 59 mm.
    assert wb.readily_available_water_mm(108.0, 0.55) == pytest.approx(59.0, abs=0.5)


# --- depletion_from_soil_moisture_mm ---------------------------------------
def test_depletion_from_soil_moisture():
    # 0.05 m3/m3 below field capacity over 0.5 m = 25 mm.
    assert wb.depletion_from_soil_moisture_mm(0.22, 0.17, 0.5) == pytest.approx(25.0)
    assert wb.depletion_from_soil_moisture_mm(0.22, 0.22, 0.5) == pytest.approx(0.0)


# --- water_stress_coefficient -----------------------------------------------
def test_ks_is_one_until_raw():
    assert wb.water_stress_coefficient(0.0, 160.0, 64.0) == 1.0
    assert wb.water_stress_coefficient(64.0, 160.0, 64.0) == 1.0


def test_ks_falls_to_zero_at_taw():
    assert wb.water_stress_coefficient(112.0, 160.0, 64.0) == pytest.approx(0.5)  # halfway
    assert wb.water_stress_coefficient(160.0, 160.0, 64.0) == pytest.approx(0.0)


# --- daily_depletion_mm -----------------------------------------------------
def test_daily_depletion_crop_use_only():
    depletion, dp = wb.daily_depletion_mm(10.0, 0.0, 0.0, 5.0, taw_mm=100.0)
    assert depletion == pytest.approx(15.0) and dp == 0.0


def test_daily_depletion_extra_water_drains_away():
    # 10 mm short, 30 mm rain, 4 mm used -> refilled, 16 mm drains (Eq. 88).
    depletion, dp = wb.daily_depletion_mm(10.0, 30.0, 0.0, 4.0, taw_mm=100.0)
    assert depletion == 0.0 and dp == pytest.approx(16.0)


def test_daily_depletion_never_exceeds_taw():
    depletion, _ = wb.daily_depletion_mm(98.0, 0.0, 0.0, 5.0, taw_mm=100.0)
    assert depletion == pytest.approx(100.0)


# --- simulate_water_balance -------------------------------------------------
def test_simulation_example_37_ten_dry_days():
    # Tomato, TAW 160 mm, RAW 64 mm, start depletion 55 mm, ET0 5, Kc 1.2, no water.
    days = 10
    result = wb.simulate_water_balance(
        start_depletion_mm=55.0, et0_mm_day=[5.0] * days, kc=[1.2] * days,
        rain_mm=[0.0] * days, irrigation_mm=[0.0] * days, taw_mm=160.0, raw_mm=64.0,
    )
    assert result["ks"].iloc[0] == 1.0 and result["ks"].iloc[1] == 1.0   # days 1-2 no stress
    assert result["etc_adj_mm"].iloc[0] == pytest.approx(6.0)
    assert result["ks"].iloc[9] == pytest.approx(0.62, abs=0.005)         # day 10
    assert result["etc_adj_mm"].iloc[9] == pytest.approx(3.7, abs=0.05)
    assert result["depletion_end_mm"].iloc[9] == pytest.approx(104.5, abs=0.1)


def test_simulation_rejects_lists_of_different_lengths():
    with pytest.raises(ValueError, match="rain_mm"):
        wb.simulate_water_balance(0.0, [5.0, 5.0], [1.0, 1.0], [0.0], [0.0, 0.0], 100.0, 40.0)
