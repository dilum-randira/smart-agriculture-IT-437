"""Stage 4: crop water need and daily root-zone soil water balance.

Source for every equation: FAO Irrigation and Drainage Paper 56 (Allen et
al., 1998), chapters 6 and 8. Equation numbers are FAO-56 numbers. Each one
is tested against FAO-56 worked examples in tests/c3/test_water_balance.py.

Crop-specific numbers (Kc values, stage lengths, root depth, p) are NOT set
here. They are passed in, so real Nai Miris values can replace the proxy
values in config.py without changing this code.

Depletion Dr is how far the root zone is below field capacity, in mm:
0 = full (field capacity), TAW = empty (wilting point).
"""

import pandas as pd


# ---------------------------------------------------------------------------
# Crop coefficient and crop water need
# ---------------------------------------------------------------------------
def kc_for_day(day: int, l_ini: int, l_dev: int, l_mid: int, l_late: int,
               kc_ini: float, kc_mid: float, kc_end: float) -> float:
    """Crop coefficient Kc on a given day of the season. FAO-56 Eq. 66.

    day: 1 = first day after planting. Stage lengths l_* are in days.
    Kc is flat in the initial and mid stages and changes in a straight line
    during the development and late stages.
    """
    if day <= l_ini:
        return kc_ini
    if day <= l_ini + l_dev:
        return kc_ini + (day - l_ini) / l_dev * (kc_mid - kc_ini)
    if day <= l_ini + l_dev + l_mid:
        return kc_mid
    previous = l_ini + l_dev + l_mid
    day_in_late = min(day - previous, l_late)      # after the season, stay at kc_end
    return kc_mid + day_in_late / l_late * (kc_end - kc_mid)


def crop_et_mm_day(kc: float, et0_mm_day: float) -> float:
    """Crop evapotranspiration ETc = Kc x ET0 in mm/day. FAO-56 Eq. 58."""
    return kc * et0_mm_day


# ---------------------------------------------------------------------------
# Root-zone water
# ---------------------------------------------------------------------------
def total_available_water_mm(field_capacity_m3m3: float, wilting_point_m3m3: float,
                             root_depth_m: float) -> float:
    """Total available water TAW in the root zone, mm. FAO-56 Eq. 82."""
    return 1000.0 * (field_capacity_m3m3 - wilting_point_m3m3) * root_depth_m


def readily_available_water_mm(taw_mm: float, p: float) -> float:
    """Readily available water RAW = p x TAW, mm. FAO-56 Eq. 83.

    p (dimensionless) is the fraction of TAW the crop can use before stress.
    """
    return p * taw_mm


def depletion_from_soil_moisture_mm(field_capacity_m3m3: float, soil_moisture_m3m3: float,
                                    root_depth_m: float) -> float:
    """Root-zone depletion Dr in mm from a measured soil moisture. FAO-56 Eq. 87.

    Lets a C1 sensor reading set today's starting depletion. The result is
    not clipped to 0..TAW here; daily_depletion_mm does that (Eq. 86).
    """
    return 1000.0 * (field_capacity_m3m3 - soil_moisture_m3m3) * root_depth_m


def water_stress_coefficient(depletion_mm: float, taw_mm: float, raw_mm: float) -> float:
    """Water stress coefficient Ks (0..1, dimensionless). FAO-56 Eq. 84.

    Ks = 1 (no stress) while depletion <= RAW, then falls in a straight line
    to 0 when depletion reaches TAW.
    """
    if depletion_mm <= raw_mm:
        return 1.0
    return max(0.0, (taw_mm - depletion_mm) / (taw_mm - raw_mm))


def daily_depletion_mm(previous_depletion_mm: float, rain_mm: float, irrigation_mm: float,
                       etc_mm: float, taw_mm: float, runoff_mm: float = 0.0,
                       capillary_rise_mm: float = 0.0) -> tuple[float, float]:
    """One day of the root-zone water balance. FAO-56 Eq. 85, 86 and 88.

    Returns (depletion at end of day in mm, deep percolation in mm).
    Water beyond field capacity drains away as deep percolation (Eq. 88).
    runoff_mm and capillary_rise_mm default to 0; capillary rise can be
    taken as 0 when the water table is deep (FAO-56 chapter 8).
    """
    depletion = (previous_depletion_mm - (rain_mm - runoff_mm) - irrigation_mm
                 - capillary_rise_mm + etc_mm)                              # Eq. 85
    deep_percolation = max(0.0, -depletion)                                 # Eq. 88
    depletion = min(max(depletion, 0.0), taw_mm)                            # Eq. 86
    return depletion, deep_percolation


# ---------------------------------------------------------------------------
# Several days in a row (e.g. the 7-day planning window)
# ---------------------------------------------------------------------------
def simulate_water_balance(start_depletion_mm: float, et0_mm_day: list[float],
                           kc: list[float], rain_mm: list[float], irrigation_mm: list[float],
                           taw_mm: float, raw_mm: float) -> pd.DataFrame:
    """Run the daily water balance over several days.

    Each day: Ks from yesterday's depletion (Eq. 84), stressed crop water use
    ETc adj = Ks x Kc x ET0 (Eq. 81), then the balance (Eq. 85).
    All lists must have one value per day.
    """
    n_days = len(et0_mm_day)
    for name, values in (("kc", kc), ("rain_mm", rain_mm), ("irrigation_mm", irrigation_mm)):
        if len(values) != n_days:
            raise ValueError(f"{name} has {len(values)} values, expected {n_days}")

    rows = []
    depletion = start_depletion_mm
    for i in range(n_days):
        ks = water_stress_coefficient(depletion, taw_mm, raw_mm)
        etc_adj = ks * crop_et_mm_day(kc[i], et0_mm_day[i])                 # Eq. 81
        depletion, deep_percolation = daily_depletion_mm(
            depletion, rain_mm[i], irrigation_mm[i], etc_adj, taw_mm)
        rows.append({
            "day": i + 1,
            "ks": ks,
            "etc_adj_mm": etc_adj,
            "depletion_end_mm": depletion,
            "deep_percolation_mm": deep_percolation,
        })
    return pd.DataFrame(rows)
