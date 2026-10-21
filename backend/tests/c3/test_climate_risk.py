"""Tests for app/c3/climate_risk.py (Stage 7). Small hand-checkable lists."""

import pytest

from app.c3 import climate_risk as cr


def test_root_rot_range_converted_from_uc_ipm_fahrenheit():
    assert cr.ROOT_ROT_TMIN_C == pytest.approx(23.9, abs=0.05)   # 75 degF
    assert cr.ROOT_ROT_TMAX_C == pytest.approx(33.3, abs=0.05)   # 92 degF


def test_heat_risk_days_threshold_edge():
    assert cr.heat_risk_days([32.9, 33.0, 35.0]) == [False, True, True]


def test_drought_risk_days():
    assert cr.drought_risk_days([1.0, 0.99, 0.0]) == [False, True, True]


def test_wet_days():
    assert cr.wet_days([0.0, 0.1, 5.0]) == [False, True, True]


def test_longest_wet_run_days():
    assert cr.longest_wet_run_days([1, 1, 0, 1, 1, 1, 0]) == 3
    assert cr.longest_wet_run_days([0, 0, 0]) == 0


def test_waterlogging_risk_days_flags_days_beyond_the_limit():
    # 3 wet days in a row with a 2-day limit: only the 3rd day is flagged.
    assert cr.waterlogging_risk_days([1, 1, 1, 0, 1], max_wet_days=2) == \
        [False, False, True, False, False]


def test_root_rot_needs_both_wet_soil_and_warm_temperature():
    dp = [5.0, 5.0, 0.0, 5.0]
    tmean = [28.0, 20.0, 28.0, 34.0]
    # wet+warm, wet but too cool, dry, wet but too hot
    assert cr.root_rot_risk_days(dp, tmean) == [True, False, False, False]


def test_summarise_risk():
    summary = cr.summarise_risk(
        tmax_c=[34.0, 30.0, 33.5], tmean_c=[28.0, 25.0, 27.0],
        ks=[1.0, 0.8, 1.0], deep_percolation_mm=[2.0, 3.0, 0.0],
    )
    assert summary == {"heat_risk_days": 2, "drought_risk_days": 1,
                       "longest_wet_run_days": 2, "root_rot_risk_days": 2}
