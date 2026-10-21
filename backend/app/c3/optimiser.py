"""Stage 9: NSGA-II multi-objective irrigation optimiser (version 2).

Decision: on which of the next 7 days to irrigate. Each irrigation refills
the root zone to field capacity (amount = that morning's depletion), as in
FAO-56 chapter 8, Example 38 (net depth <= depletion; a full refill avoids
deep percolation). An irrigation is skipped if it would apply less than
min_irrigation_mm (the minimum practical amount for the irrigation method).

Objectives (all minimised):
1. total_water_mm       - net irrigation over the 7 days (forecast scenario).
2. relative_et_deficit  - 1 - ETa/ETm in the WORST weather scenario. FAO-33
                          (Doorenbos and Kassam, 1979): 1 - Ya/Ym =
                          Ky (1 - ETa/ETm), so a smaller deficit means a
                          smaller yield loss for any Ky > 0.
3. irrigation_events    - number of irrigations (labour / pumping effort).
4. root_rot_risk_days   - days with water beyond field capacity and Tmean
                          in the Phytophthora range (climate_risk.py, UC IPM),
                          forecast scenario.
Heat risk is not an objective: irrigation cannot change air temperature.
Cost is not separate yet: without a water price it equals objective 1.
"""

import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize

from app.c3 import climate_risk as cr
from app.c3 import et0 as et0_module
from app.c3 import water_balance as wb

OBJECTIVES = ["total_water_mm", "relative_et_deficit", "irrigation_events", "root_rot_risk_days"]

# NSGA-II settings chosen with scripts/tune_nsga2.py on the SYNTHETIC
# forecasts: the cheapest setting in the tested grid that found the exact
# Pareto front in all 120 test cases (pop 60 x 80 generations). Algorithm
# settings, not agronomic values; re-tune on real data.
DEFAULT_POP_SIZE = 60
DEFAULT_N_GENERATIONS = 80


@dataclass
class WeatherScenario:
    """One possible weather path over the planning window (one value per day)."""
    name: str
    et0_mm_day: list[float]
    rain_mm: list[float]
    tmean_c: list[float]


# ---------------------------------------------------------------------------
# Evaluating one plan
# ---------------------------------------------------------------------------
def relative_et_deficit(eta_mm: float, etm_mm: float) -> float:
    """1 - ETa/ETm (dimensionless, 0 = no water stress). FAO-33 yield response."""
    if etm_mm <= 0:
        return 0.0
    return 1.0 - eta_mm / etm_mm


def run_schedule(irrigate: list[bool], start_depletion_mm: float, scenario: WeatherScenario,
                 kc: list[float], taw_mm: float, raw_mm: float,
                 min_irrigation_mm: float = 0.0) -> dict:
    """Water balance for an irrigation plan under one weather scenario.

    Same daily order as baselines.simulate_with_rule (FAO-56 Example 38):
    irrigate in the morning (refill to field capacity), Ks after irrigation
    (Eq. 84), ETa = Ks x Kc x ET0 (Eq. 81), then the balance (Eq. 85, 86, 88).
    Kept free of pandas so the optimiser can call it thousands of times.
    """
    depletion = start_depletion_mm
    water = 0.0
    events = 0
    eta_total = etm_total = 0.0
    percolation = []
    for day, wanted in enumerate(irrigate):
        irrigation = depletion if (wanted and depletion >= min_irrigation_mm and depletion > 0) else 0.0
        if irrigation > 0:
            water += irrigation
            events += 1
        ks = wb.water_stress_coefficient(depletion - irrigation, taw_mm, raw_mm)
        etm = wb.crop_et_mm_day(kc[day], scenario.et0_mm_day[day])   # ETc without stress
        eta = ks * etm                                               # ETc adj, Eq. 81
        depletion, dp = wb.daily_depletion_mm(depletion, scenario.rain_mm[day], irrigation,
                                              eta, taw_mm)
        eta_total += eta
        etm_total += etm
        percolation.append(dp)
    return {
        "total_water_mm": water,
        "irrigation_events": events,
        "relative_et_deficit": relative_et_deficit(eta_total, etm_total),
        "root_rot_risk_days": sum(cr.root_rot_risk_days(percolation, scenario.tmean_c)),
        "deep_percolation_mm": sum(percolation),
        "end_depletion_mm": depletion,
    }


def evaluate_schedule(irrigate: list[bool], start_depletion_mm: float,
                      scenarios: list[WeatherScenario], kc: list[float], taw_mm: float,
                      raw_mm: float, min_irrigation_mm: float = 0.0) -> list[float]:
    """The four objective values for one plan (order as in OBJECTIVES).

    ET deficit comes from the worst scenario (protects the crop); water,
    events and root-rot risk from the first scenario (the forecast itself).
    """
    results = [run_schedule(irrigate, start_depletion_mm, s, kc, taw_mm, raw_mm, min_irrigation_mm)
               for s in scenarios]
    forecast = results[0]
    return [forecast["total_water_mm"],
            max(r["relative_et_deficit"] for r in results),
            float(forecast["irrigation_events"]),
            float(forecast["root_rot_risk_days"])]


def _check_scenarios(scenarios: list[WeatherScenario], n_days: int) -> None:
    for s in scenarios:
        if not (len(s.et0_mm_day) == len(s.rain_mm) == len(s.tmean_c) == n_days):
            raise ValueError(f"scenario '{s.name}' must have {n_days} days")


def _plans_table(plans: list[list[bool]], objectives: list[list[float]]) -> pd.DataFrame:
    rows = []
    for plan, f in zip(plans, objectives):
        row = {f"day{d + 1}_irrigate": bool(v) for d, v in enumerate(plan)}
        row.update(dict(zip(OBJECTIVES, f)))
        rows.append(row)
    table = pd.DataFrame(rows).drop_duplicates()
    return table.sort_values(OBJECTIVES).reset_index(drop=True)


# ---------------------------------------------------------------------------
# NSGA-II
# ---------------------------------------------------------------------------
class IrrigationProblem(ElementwiseProblem):
    """pymoo problem: one variable per day in [0, 1]; >= 0.5 means irrigate."""

    def __init__(self, start_depletion_mm: float, scenarios: list[WeatherScenario],
                 kc: list[float], taw_mm: float, raw_mm: float, min_irrigation_mm: float):
        self.args = (start_depletion_mm, scenarios, kc, taw_mm, raw_mm, min_irrigation_mm)
        super().__init__(n_var=len(kc), n_obj=len(OBJECTIVES), xl=0.0, xu=1.0)

    def _evaluate(self, x, out, *args, **kwargs):
        start, scenarios, kc, taw, raw, min_mm = self.args
        out["F"] = evaluate_schedule(list(x >= 0.5), start, scenarios, kc, taw, raw, min_mm)


def optimise_schedule(start_depletion_mm: float, scenarios: list[WeatherScenario],
                      kc: list[float], taw_mm: float, raw_mm: float,
                      min_irrigation_mm: float = 0.0, pop_size: int = DEFAULT_POP_SIZE,
                      n_generations: int = DEFAULT_N_GENERATIONS, seed: int = 1) -> pd.DataFrame:
    """Run NSGA-II; return the Pareto front, one row per distinct plan."""
    _check_scenarios(scenarios, len(kc))
    problem = IrrigationProblem(start_depletion_mm, scenarios, kc, taw_mm, raw_mm, min_irrigation_mm)
    result = minimize(problem, NSGA2(pop_size=pop_size), ("n_gen", n_generations),
                      seed=seed, verbose=False)
    plans = [list(x >= 0.5) for x in np.atleast_2d(result.X)]
    return _plans_table(plans, np.atleast_2d(result.F).tolist())


def all_schedules(start_depletion_mm: float, scenarios: list[WeatherScenario],
                  kc: list[float], taw_mm: float, raw_mm: float,
                  min_irrigation_mm: float = 0.0) -> pd.DataFrame:
    """Every possible plan (2^days of them). Used to check / tune NSGA-II."""
    _check_scenarios(scenarios, len(kc))
    plans = [list(p) for p in itertools.product([False, True], repeat=len(kc))]
    objectives = [evaluate_schedule(p, start_depletion_mm, scenarios, kc, taw_mm, raw_mm,
                                    min_irrigation_mm) for p in plans]
    return _plans_table(plans, objectives)


def pareto_front(table: pd.DataFrame) -> pd.DataFrame:
    """Rows not dominated by any other row (no other row is at least as good
    on every objective and strictly better on one). Duplicate objective
    vectors are kept once."""
    values = table[OBJECTIVES].to_numpy()
    keep = []
    for i, v in enumerate(values):
        dominated = np.any(np.all(values <= v, axis=1) & np.any(values < v, axis=1))
        keep.append(not dominated)
    front = table[keep].drop_duplicates(subset=OBJECTIVES)
    return front.reset_index(drop=True)


def least_water_schedule(front: pd.DataFrame, max_relative_et_deficit: float) -> pd.Series:
    """Plan using least water whose ET deficit <= max_relative_et_deficit.

    Ties are broken by fewer irrigation events, then fewer root-rot risk days.
    The allowed deficit is a farmer / C4 choice, so it must be passed in.
    Raises ValueError if no plan qualifies.
    """
    ok = front[front["relative_et_deficit"] <= max_relative_et_deficit + 1e-12]
    if ok.empty:
        raise ValueError("no schedule meets the allowed ET deficit")
    return ok.sort_values(["total_water_mm", "irrigation_events", "root_rot_risk_days"]).iloc[0]


# ---------------------------------------------------------------------------
# Building scenarios from forecasts
# ---------------------------------------------------------------------------
def forecast_scenarios(forecasts: pd.DataFrame, issue_date: str,
                       latitude_deg: float, elevation_m: float) -> list[WeatherScenario]:
    """Weather scenarios for one forecast issue (from data_loading.load_forecasts).

    - "forecast": the forecast rain
    - "no_rain":  the forecast rain does not arrive
    Both use FAO-56 Penman-Monteith ET0 and Tmean = (Tmax + Tmin) / 2 (Eq. 9).
    """
    issue = forecasts[forecasts["issue_date"] == pd.Timestamp(issue_date)]
    if issue.empty:
        raise ValueError(f"no forecast issued on {issue_date}")
    issue = issue.sort_values("lead_day").rename(columns={"target_date": "date"})
    with_et0 = et0_module.add_et0_column(issue, latitude_deg, elevation_m)
    et0_values = with_et0["et0_mm_day"].tolist()
    tmean = ((with_et0["tmax_c"] + with_et0["tmin_c"]) / 2.0).tolist()
    return [
        WeatherScenario("forecast", et0_values, with_et0["rainfall_mm"].tolist(), tmean),
        WeatherScenario("no_rain", et0_values, [0.0] * len(et0_values), tmean),
    ]
