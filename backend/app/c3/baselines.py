"""Stage 8 (part 1): baseline irrigation schedules to compare C3 against.

An "irrigation rule" is any function  rule(day, depletion_mm) -> irrigation_mm
that decides, at the start of each day, how much water to apply (net mm).
The same simulator runs every rule, so baselines and the later NSGA-II
schedules are compared on exactly the same water balance (Stage 4).

Baselines here:
1. Fixed threshold (FAO-56 chapter 8, Example 38): irrigate when root-zone
   depletion reaches RAW, and refill to field capacity.
2. DoA Sri Lanka interval schedule (HORDI capsicum guidance): irrigate every
   4-5 days early in the season and every week later.
The reactive ML baseline ("Paper 8") is added later.
"""

from typing import Callable

import pandas as pd

from app.c3 import water_balance as wb

IrrigationRule = Callable[[int, float], float]


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
def no_irrigation_rule(day: int, depletion_mm: float) -> float:
    """Never irrigate (rain only). Useful as a reference."""
    return 0.0


def fixed_threshold_rule(raw_mm: float) -> IrrigationRule:
    """Irrigate when depletion >= RAW; apply exactly the depletion (refill to FC).

    Source: FAO-56 chapter 8, Example 38: "Irrigation is required when
    Dr,i >= RAW", and the net depth should be <= the root-zone depletion;
    applying the full depletion refills the root zone with no deep percolation.
    """
    def rule(day: int, depletion_mm: float) -> float:
        return depletion_mm if depletion_mm >= raw_mm else 0.0
    return rule


def doa_irrigation_days(season_days: int, interval_early_days: int,
                        interval_late_days: int, early_stage_end_day: int) -> list[int]:
    """Days of the season (1 = first day) on which the DoA schedule irrigates.

    Source for the intervals: DoA Sri Lanka, HORDI capsicum page: "Irrigation
    to be practiced in 4-5 day intervals at early stages and 1 week interval
    at latter stages of the crop." HORDI does not say on which day "early"
    ends, so early_stage_end_day must be chosen and justified by the caller.
    """
    days = []
    day = interval_early_days
    while day <= season_days:
        days.append(day)
        interval = interval_early_days if day < early_stage_end_day else interval_late_days
        day += interval
    return days


def doa_schedule_rule(irrigation_days: list[int]) -> IrrigationRule:
    """Irrigate on the given days, refilling the root zone to field capacity.

    ASSUMPTION: HORDI gives intervals but not amounts, so each irrigation
    refills the root zone (amount = depletion). State this in the thesis.
    """
    days = set(irrigation_days)

    def rule(day: int, depletion_mm: float) -> float:
        return depletion_mm if day in days else 0.0
    return rule


def stage_aware_rule(taw_mm: float, depletion_fraction_by_day: list[float],
                     refill_fraction_by_day: list[float]) -> IrrigationRule:
    """Stage 5: irrigate when depletion reaches a day-specific fraction of TAW,
    and refill only a day-specific fraction of the depletion.

    Normal stages: fraction = the crop's p (FAO-56 Table 22) and refill 1.0,
    which is the fixed threshold rule. Deficit at flowering: a larger
    fraction and/or a refill below 1.0, allowing controlled stress (see
    growth_stages.py for the evidence and its limits). Build the daily lists
    with growth_stages.daily_values_by_stage. The deficit values have no
    source yet and must be chosen and justified by the caller.
    """
    def rule(day: int, depletion_mm: float) -> float:
        trigger_mm = depletion_fraction_by_day[day - 1] * taw_mm
        if depletion_mm >= trigger_mm:
            return refill_fraction_by_day[day - 1] * depletion_mm
        return 0.0
    return rule


# ---------------------------------------------------------------------------
# Running a rule and summarising the result
# ---------------------------------------------------------------------------
def simulate_with_rule(rule: IrrigationRule, start_depletion_mm: float,
                       et0_mm_day: list[float], kc: list[float], rain_mm: list[float],
                       taw_mm: float, raw_mm: float) -> pd.DataFrame:
    """Daily water balance where `rule` decides irrigation each morning.

    Order within a day, as in FAO-56 Example 38: irrigate first, then Ks is
    found from the depletion after irrigation (Eq. 84), then crop water use
    ETc adj = Ks x Kc x ET0 (Eq. 81), then the balance (Eq. 85, 86, 88).
    """
    n_days = len(et0_mm_day)
    for name, values in (("kc", kc), ("rain_mm", rain_mm)):
        if len(values) != n_days:
            raise ValueError(f"{name} has {len(values)} values, expected {n_days}")

    rows = []
    depletion = start_depletion_mm
    for i in range(n_days):
        day = i + 1
        irrigation = rule(day, depletion)
        depletion_after_irrigation = max(0.0, depletion - irrigation)
        ks = wb.water_stress_coefficient(depletion_after_irrigation, taw_mm, raw_mm)
        etc_adj = ks * wb.crop_et_mm_day(kc[i], et0_mm_day[i])
        depletion, deep_percolation = wb.daily_depletion_mm(
            depletion, rain_mm[i], irrigation, etc_adj, taw_mm)
        rows.append({
            "day": day,
            "irrigation_mm": irrigation,
            "ks": ks,
            "etc_adj_mm": etc_adj,
            "depletion_end_mm": depletion,
            "deep_percolation_mm": deep_percolation,
        })
    return pd.DataFrame(rows)


def summarise_schedule(result: pd.DataFrame) -> dict:
    """Key numbers for comparing schedules (all from the simulated table)."""
    return {
        "total_irrigation_mm": float(result["irrigation_mm"].sum()),
        "irrigation_events": int((result["irrigation_mm"] > 0).sum()),
        "stress_days": int((result["ks"] < 1.0).sum()),          # days with Ks < 1
        "mean_ks": float(result["ks"].mean()),
        "total_etc_adj_mm": float(result["etc_adj_mm"].sum()),
        "total_deep_percolation_mm": float(result["deep_percolation_mm"].sum()),
    }
