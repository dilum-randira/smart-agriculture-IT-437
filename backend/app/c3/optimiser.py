"""Stage 9: NSGA-II multi-objective irrigation optimiser (prototype).

Decision: net irrigation (mm) on each of the next 7 days.

Objectives (all minimised):
1. total_water_mm         - water applied over the planning window.
2. relative_et_deficit    - 1 - ETa/ETm, the crop's water shortfall
                            (0 = no stress). FAO-33 (Doorenbos and Kassam,
                            1979): 1 - Ya/Ym = Ky (1 - ETa/ETm), so for any
                            Ky > 0 a smaller ET deficit means a smaller yield
                            loss. This works before Ky for Nai Miris is known.
3. deep_percolation_mm    - water lost below the root zone (wasted).

Uncertainty: objective 2 is taken from the WORST of several weather
scenarios (for example C2's forecast rain and a no-rain case), so the plan
still protects the crop if forecast rain does not arrive.

Not included yet: cost (needs the water price; until then it is just
water x price, the same as objective 1) and climate risk (Stage 7).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize

from app.c3 import et0 as et0_module
from app.c3 import water_balance as wb


@dataclass
class WeatherScenario:
    """One possible weather path over the planning window (one value per day)."""
    name: str
    et0_mm_day: list[float]
    rain_mm: list[float]


# ---------------------------------------------------------------------------
# Evaluating one schedule
# ---------------------------------------------------------------------------
def relative_et_deficit(eta_mm: float, etm_mm: float) -> float:
    """1 - ETa/ETm (dimensionless, 0 = no water stress). FAO-33 yield response."""
    if etm_mm <= 0:
        return 0.0
    return 1.0 - eta_mm / etm_mm


def run_schedule(irrigation_mm: list[float], start_depletion_mm: float,
                 scenario: WeatherScenario, kc: list[float],
                 taw_mm: float, raw_mm: float) -> dict:
    """Water balance for a fixed irrigation plan under one weather scenario.

    Same daily order as baselines.simulate_with_rule (FAO-56 Example 38):
    irrigate in the morning, Ks after irrigation (Eq. 84), ETa = Ks x Kc x ET0
    (Eq. 81), then the balance (Eq. 85, 86, 88). Kept free of pandas so the
    optimiser can call it thousands of times quickly.
    """
    depletion = start_depletion_mm
    eta_total = etm_total = percolation_total = 0.0
    for day, irrigation in enumerate(irrigation_mm):
        ks = wb.water_stress_coefficient(max(0.0, depletion - irrigation), taw_mm, raw_mm)
        etm = wb.crop_et_mm_day(kc[day], scenario.et0_mm_day[day])   # ETc without stress
        eta = ks * etm                                               # ETc adj, Eq. 81
        depletion, percolation = wb.daily_depletion_mm(
            depletion, scenario.rain_mm[day], irrigation, eta, taw_mm)
        eta_total += eta
        etm_total += etm
        percolation_total += percolation
    return {
        "eta_mm": eta_total,
        "etm_mm": etm_total,
        "relative_et_deficit": relative_et_deficit(eta_total, etm_total),
        "deep_percolation_mm": percolation_total,
        "end_depletion_mm": depletion,
    }


def evaluate_schedule(irrigation_mm: list[float], start_depletion_mm: float,
                      scenarios: list[WeatherScenario], kc: list[float],
                      taw_mm: float, raw_mm: float) -> tuple[float, float, float]:
    """The three objective values for one schedule.

    ET deficit: worst scenario (protects the crop).
    Deep percolation: first scenario (the forecast itself), because extra
    rain in other scenarios is not caused by the plan.
    """
    results = [run_schedule(irrigation_mm, start_depletion_mm, s, kc, taw_mm, raw_mm)
               for s in scenarios]
    total_water = float(sum(irrigation_mm))
    worst_deficit = max(r["relative_et_deficit"] for r in results)
    percolation = results[0]["deep_percolation_mm"]
    return total_water, worst_deficit, percolation


# ---------------------------------------------------------------------------
# NSGA-II
# ---------------------------------------------------------------------------
class IrrigationProblem(ElementwiseProblem):
    """pymoo problem: one decision variable per day, three objectives."""

    def __init__(self, start_depletion_mm: float, scenarios: list[WeatherScenario],
                 kc: list[float], taw_mm: float, raw_mm: float):
        self.start_depletion_mm = start_depletion_mm
        self.scenarios = scenarios
        self.kc = kc
        self.taw_mm = taw_mm
        self.raw_mm = raw_mm
        n_days = len(kc)
        # Upper bound per day = TAW: FAO-56 ch. 8 says net irrigation should
        # not exceed the root-zone depletion, which is at most TAW (Eq. 86).
        super().__init__(n_var=n_days, n_obj=3, xl=0.0, xu=taw_mm)

    def _evaluate(self, x, out, *args, **kwargs):
        out["F"] = list(evaluate_schedule(list(x), self.start_depletion_mm, self.scenarios,
                                          self.kc, self.taw_mm, self.raw_mm))


def optimise_schedule(start_depletion_mm: float, scenarios: list[WeatherScenario],
                      kc: list[float], taw_mm: float, raw_mm: float,
                      pop_size: int = 60, n_generations: int = 100,
                      seed: int = 1) -> pd.DataFrame:
    """Run NSGA-II and return the Pareto front, one row per schedule.

    pop_size, n_generations and seed are ALGORITHM settings, not agronomic
    values; pop_size 60 / 100 generations are a starting point to be tuned.
    """
    for s in scenarios:
        if len(s.et0_mm_day) != len(kc) or len(s.rain_mm) != len(kc):
            raise ValueError(f"scenario '{s.name}' must have {len(kc)} days")
    problem = IrrigationProblem(start_depletion_mm, scenarios, kc, taw_mm, raw_mm)
    result = minimize(problem, NSGA2(pop_size=pop_size), ("n_gen", n_generations),
                      seed=seed, verbose=False)
    schedules = np.atleast_2d(result.X)
    objectives = np.atleast_2d(result.F)
    rows = []
    for x, f in zip(schedules, objectives):
        row = {f"day{d + 1}_mm": float(v) for d, v in enumerate(x)}
        row.update(total_water_mm=float(f[0]), relative_et_deficit=float(f[1]),
                   deep_percolation_mm=float(f[2]))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("total_water_mm").reset_index(drop=True)


def least_water_schedule(front: pd.DataFrame, max_relative_et_deficit: float) -> pd.Series:
    """From the Pareto front, the schedule using least water whose ET deficit
    is at most max_relative_et_deficit.

    The allowed deficit is a decision for the farmer / C4, not a constant,
    so it must be passed in. Raises ValueError if no schedule qualifies.
    """
    ok = front[front["relative_et_deficit"] <= max_relative_et_deficit]
    if ok.empty:
        raise ValueError("no schedule meets the allowed ET deficit")
    return ok.sort_values("total_water_mm").iloc[0]


# ---------------------------------------------------------------------------
# Building scenarios from C2 forecasts
# ---------------------------------------------------------------------------
def forecast_scenarios(forecasts: pd.DataFrame, issue_date: str,
                       latitude_deg: float, elevation_m: float) -> list[WeatherScenario]:
    """Weather scenarios for one C2 forecast issue (from data_loading.load_forecasts).

    Returns two scenarios with the same ET0 (FAO-56 Penman-Monteith):
    - "forecast": C2's forecast rain
    - "no_rain":  the forecast rain does not arrive
    """
    issue = forecasts[forecasts["issue_date"] == pd.Timestamp(issue_date)]
    if issue.empty:
        raise ValueError(f"no forecast issued on {issue_date}")
    issue = issue.sort_values("lead_day").rename(columns={"target_date": "date"})
    with_et0 = et0_module.add_et0_column(issue, latitude_deg, elevation_m)
    et0_values = with_et0["et0_mm_day"].tolist()
    return [
        WeatherScenario("forecast", et0_values, with_et0["rainfall_mm"].tolist()),
        WeatherScenario("no_rain", et0_values, [0.0] * len(et0_values)),
    ]
