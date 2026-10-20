"""Stage 3: daily reference evapotranspiration (ET0) with FAO-56 Penman-Monteith.

Source for every equation: Allen, R.G., Pereira, L.S., Raes, D. and Smith, M.
(1998) Crop evapotranspiration. FAO Irrigation and Drainage Paper 56 ("FAO-56").
Equation numbers below are FAO-56 equation numbers. Each one is tested
against FAO-56's own worked examples in tests/c3/test_et0.py.

Functions work on single numbers and on pandas columns / numpy arrays.
"""

import numpy as np
import pandas as pd

ALBEDO_GRASS = 0.23            # dimensionless, reference grass albedo, FAO-56 Eq. 38
STEFAN_BOLTZMANN = 4.903e-9    # MJ/K4/m2/day, FAO-56 Eq. 39
KELVIN_OFFSET = 273.16         # degC -> K, as used in FAO-56 Eq. 39 and Example 18


# ---------------------------------------------------------------------------
# Air properties
# ---------------------------------------------------------------------------
def atmospheric_pressure_kpa(elevation_m):
    """Atmospheric pressure P in kPa from elevation in m. FAO-56 Eq. 7."""
    return 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26


def psychrometric_constant_kpa_per_c(pressure_kpa):
    """Psychrometric constant gamma in kPa/degC. FAO-56 Eq. 8."""
    return 0.665e-3 * pressure_kpa


def saturation_vapour_pressure_kpa(temp_c):
    """Saturation vapour pressure e0(T) in kPa at temperature T in degC. FAO-56 Eq. 11."""
    return 0.6108 * np.exp(17.27 * temp_c / (temp_c + 237.3))


def mean_saturation_vapour_pressure_kpa(tmax_c, tmin_c):
    """Mean saturation vapour pressure es in kPa. FAO-56 Eq. 12."""
    return (saturation_vapour_pressure_kpa(tmax_c) + saturation_vapour_pressure_kpa(tmin_c)) / 2.0


def slope_vapour_pressure_curve_kpa_per_c(tmean_c):
    """Slope of the saturation vapour pressure curve (delta) in kPa/degC. FAO-56 Eq. 13."""
    return 4098.0 * saturation_vapour_pressure_kpa(tmean_c) / (tmean_c + 237.3) ** 2


def actual_vapour_pressure_from_rh_mean_kpa(tmax_c, tmin_c, rh_mean_pct):
    """Actual vapour pressure ea in kPa from mean relative humidity. FAO-56 Eq. 19.

    FAO-56 calls this the least preferred humidity method (Eq. 17 with
    RHmax and RHmin is better). It is used because the input files only
    have rh_mean_pct.
    """
    return rh_mean_pct / 100.0 * mean_saturation_vapour_pressure_kpa(tmax_c, tmin_c)


# ---------------------------------------------------------------------------
# Radiation
# ---------------------------------------------------------------------------
def extraterrestrial_radiation_mj_m2_day(day_of_year, latitude_deg):
    """Extraterrestrial radiation Ra in MJ/m2/day. FAO-56 Eq. 21 (with Eq. 22-25)."""
    phi = np.pi / 180.0 * latitude_deg                                      # Eq. 22
    dr = 1 + 0.033 * np.cos(2 * np.pi * day_of_year / 365)                 # Eq. 23
    delta = 0.409 * np.sin(2 * np.pi * day_of_year / 365 - 1.39)           # Eq. 24
    ws = np.arccos(-np.tan(phi) * np.tan(delta))                           # Eq. 25
    gsc = 0.0820  # MJ/m2/min, solar constant, FAO-56 Eq. 21
    return (24 * 60 / np.pi) * gsc * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws)
    )


def clear_sky_radiation_mj_m2_day(ra_mj_m2_day, elevation_m):
    """Clear-sky solar radiation Rso in MJ/m2/day. FAO-56 Eq. 37."""
    return (0.75 + 2e-5 * elevation_m) * ra_mj_m2_day


def net_shortwave_radiation_mj_m2_day(rs_mj_m2_day):
    """Net shortwave radiation Rns in MJ/m2/day for reference grass. FAO-56 Eq. 38."""
    return (1 - ALBEDO_GRASS) * rs_mj_m2_day


def net_longwave_radiation_mj_m2_day(tmax_c, tmin_c, ea_kpa, rs_mj_m2_day, rso_mj_m2_day):
    """Net outgoing longwave radiation Rnl in MJ/m2/day. FAO-56 Eq. 39.

    Rs/Rso is capped at 1.0, as FAO-56 requires (Rs/Rso <= 1.0).
    """
    tmax_k4 = (tmax_c + KELVIN_OFFSET) ** 4
    tmin_k4 = (tmin_c + KELVIN_OFFSET) ** 4
    rs_over_rso = np.minimum(rs_mj_m2_day / rso_mj_m2_day, 1.0)
    return (STEFAN_BOLTZMANN * (tmax_k4 + tmin_k4) / 2
            * (0.34 - 0.14 * np.sqrt(ea_kpa))
            * (1.35 * rs_over_rso - 0.35))


# ---------------------------------------------------------------------------
# Penman-Monteith
# ---------------------------------------------------------------------------
def penman_monteith_mm_day(tmean_c, delta_kpa_per_c, gamma_kpa_per_c, rn_mj_m2_day,
                           g_mj_m2_day, u2_m_s, es_kpa, ea_kpa):
    """FAO Penman-Monteith reference evapotranspiration ET0 in mm/day. FAO-56 Eq. 6."""
    numerator = (0.408 * delta_kpa_per_c * (rn_mj_m2_day - g_mj_m2_day)
                 + gamma_kpa_per_c * 900.0 / (tmean_c + 273.0) * u2_m_s * (es_kpa - ea_kpa))
    denominator = delta_kpa_per_c + gamma_kpa_per_c * (1 + 0.34 * u2_m_s)
    return numerator / denominator


def et0_daily_mm(tmax_c, tmin_c, ea_kpa, rs_mj_m2_day, u2_m_s,
                 latitude_deg, elevation_m, day_of_year):
    """Daily ET0 in mm/day from daily weather, following FAO-56 Example 18.

    Soil heat flux G is taken as 0 for daily steps (FAO-56 Eq. 42).
    """
    tmean_c = (tmax_c + tmin_c) / 2.0                                      # Eq. 9
    delta = slope_vapour_pressure_curve_kpa_per_c(tmean_c)
    gamma = psychrometric_constant_kpa_per_c(atmospheric_pressure_kpa(elevation_m))
    es = mean_saturation_vapour_pressure_kpa(tmax_c, tmin_c)

    ra = extraterrestrial_radiation_mj_m2_day(day_of_year, latitude_deg)
    rso = clear_sky_radiation_mj_m2_day(ra, elevation_m)
    rns = net_shortwave_radiation_mj_m2_day(rs_mj_m2_day)
    rnl = net_longwave_radiation_mj_m2_day(tmax_c, tmin_c, ea_kpa, rs_mj_m2_day, rso)
    rn = rns - rnl                                                          # Eq. 40

    return penman_monteith_mm_day(tmean_c, delta, gamma, rn, 0.0, u2_m_s, es, ea_kpa)


def add_et0_column(weather: pd.DataFrame, latitude_deg: float, elevation_m: float) -> pd.DataFrame:
    """Return a copy of a daily weather table (from data_loading.load_weather)
    with an extra 'et0_mm_day' column.
    """
    out = weather.copy()
    ea = actual_vapour_pressure_from_rh_mean_kpa(out["tmax_c"], out["tmin_c"], out["rh_mean_pct"])
    out["et0_mm_day"] = et0_daily_mm(
        out["tmax_c"], out["tmin_c"], ea, out["solar_radiation_mj_m2_day"],
        out["wind_speed_2m_ms"], latitude_deg, elevation_m, out["date"].dt.dayofyear,
    )
    return out
