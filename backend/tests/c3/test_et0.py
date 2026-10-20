"""Tests for app/c3/et0.py, checked against FAO-56 worked examples.

Expected values are copied from FAO Irrigation and Drainage Paper 56
(Allen et al., 1998), chapter 3 (Examples 2, 3, 8) and chapter 4 (Example 18).
FAO-56 prints rounded numbers, so each test allows a small rounding margin.
"""

import pytest

from app.c3 import config
from app.c3 import data_loading as dl
from app.c3 import et0

# FAO-56 Example 18 inputs: Uccle (Brussels), 6 July (day 187), 50.80 degN, 100 m.
EX18 = dict(tmax_c=21.5, tmin_c=12.3, ea_kpa=1.409, rs_mj_m2_day=22.07,
            u2_m_s=2.078, latitude_deg=50.80, elevation_m=100.0, day_of_year=187)


# --- air properties ---------------------------------------------------------
def test_atmospheric_pressure_example_2():
    assert et0.atmospheric_pressure_kpa(1800.0) == pytest.approx(81.8, abs=0.05)


def test_atmospheric_pressure_example_18():
    assert et0.atmospheric_pressure_kpa(100.0) == pytest.approx(100.1, abs=0.05)


def test_psychrometric_constant_example_2():
    assert et0.psychrometric_constant_kpa_per_c(81.8) == pytest.approx(0.054, abs=0.0005)


def test_saturation_vapour_pressure_example_3():
    assert et0.saturation_vapour_pressure_kpa(24.5) == pytest.approx(3.075, abs=0.0005)
    assert et0.saturation_vapour_pressure_kpa(15.0) == pytest.approx(1.705, abs=0.0005)


def test_mean_saturation_vapour_pressure_examples_3_and_18():
    assert et0.mean_saturation_vapour_pressure_kpa(24.5, 15.0) == pytest.approx(2.39, abs=0.005)
    assert et0.mean_saturation_vapour_pressure_kpa(21.5, 12.3) == pytest.approx(1.997, abs=0.0005)


def test_slope_vapour_pressure_curve_example_18():
    assert et0.slope_vapour_pressure_curve_kpa_per_c(16.9) == pytest.approx(0.122, abs=0.0005)


def test_actual_vapour_pressure_from_rh_mean():
    # Eq. 19: ea is RHmean % of es, so 50 % gives half of es.
    es = et0.mean_saturation_vapour_pressure_kpa(30.0, 22.0)
    assert et0.actual_vapour_pressure_from_rh_mean_kpa(30.0, 22.0, 50.0) == pytest.approx(es / 2)
    assert et0.actual_vapour_pressure_from_rh_mean_kpa(30.0, 22.0, 100.0) == pytest.approx(es)


# --- radiation --------------------------------------------------------------
def test_extraterrestrial_radiation_example_8():
    # Rio de Janeiro example uses 20 degS on 3 September (day 246).
    assert et0.extraterrestrial_radiation_mj_m2_day(246, -20.0) == pytest.approx(32.2, abs=0.05)


def test_extraterrestrial_radiation_example_18():
    assert et0.extraterrestrial_radiation_mj_m2_day(187, 50.80) == pytest.approx(41.09, abs=0.05)


def test_clear_sky_radiation_example_18():
    assert et0.clear_sky_radiation_mj_m2_day(41.09, 100.0) == pytest.approx(30.90, abs=0.05)


def test_net_shortwave_radiation_example_18():
    assert et0.net_shortwave_radiation_mj_m2_day(22.07) == pytest.approx(17.00, abs=0.01)


def test_net_longwave_radiation_example_18():
    rnl = et0.net_longwave_radiation_mj_m2_day(21.5, 12.3, 1.409, 22.07, 30.90)
    assert rnl == pytest.approx(3.71, abs=0.02)


def test_net_longwave_radiation_caps_rs_over_rso_at_one():
    # Rs larger than Rso must give the same result as Rs equal to Rso.
    capped = et0.net_longwave_radiation_mj_m2_day(30.0, 22.0, 2.5, 30.0, 25.0)
    equal = et0.net_longwave_radiation_mj_m2_day(30.0, 22.0, 2.5, 25.0, 25.0)
    assert capped == pytest.approx(equal)


# --- Penman-Monteith --------------------------------------------------------
def test_penman_monteith_with_example_18_intermediate_values():
    result = et0.penman_monteith_mm_day(
        tmean_c=16.9, delta_kpa_per_c=0.122, gamma_kpa_per_c=0.0666, rn_mj_m2_day=13.28,
        g_mj_m2_day=0.0, u2_m_s=2.078, es_kpa=1.997, ea_kpa=1.409,
    )
    assert result == pytest.approx(3.88, abs=0.03)   # FAO-56 prints 3.88 -> 3.9 mm/day


def test_et0_daily_example_18_from_raw_inputs():
    assert et0.et0_daily_mm(**EX18) == pytest.approx(3.88, abs=0.05)


# --- whole weather table ----------------------------------------------------
def test_add_et0_column_on_synthetic_weather():
    weather = dl.load_weather(config.SAMPLE_DATA_DIR / "weather_synthetic_daily.csv")
    out = et0.add_et0_column(weather, latitude_deg=7.9, elevation_m=150.0)
    assert "et0_mm_day" in out.columns
    assert "et0_mm_day" not in weather.columns          # input not changed
    assert out["et0_mm_day"].notna().all()
    assert (out["et0_mm_day"] > 0).all()
