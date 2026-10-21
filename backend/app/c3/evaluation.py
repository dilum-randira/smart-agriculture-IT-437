"""Stage 11: compare irrigation schedules over a whole season.

Every schedule is an irrigation rule run by baselines.simulate_with_rule on
the same "true" weather, so the comparison is fair. The NSGA-II optimiser is
turned into a rule that re-plans every morning (receding horizon): it uses
the C2 forecast issued the day before, plans 7 days, and applies only day 1.

ASSUMPTIONS (state these with any result):
- The season starts at field capacity (depletion 0), i.e. after a
  transplanting irrigation.
- The optimiser knows the true current depletion (a perfect soil sensor).
"""

import pandas as pd

from app.c3 import baselines as bl
from app.c3 import climate_risk as cr
from app.c3 import et0 as et0_module
from app.c3 import optimiser as opt


def season_truth(weather: pd.DataFrame, start_date: str, n_days: int,
                 latitude_deg: float, elevation_m: float) -> pd.DataFrame:
    """The 'true' daily weather for the season, with ET0 (mm/day) added.

    weather comes from data_loading.load_weather. Raises ValueError if the
    file does not cover the whole season.
    """
    dates = pd.date_range(start_date, periods=n_days, freq="D")
    season = weather[weather["date"].isin(dates)].sort_values("date")
    if len(season) != n_days:
        raise ValueError(f"weather covers {len(season)} of {n_days} season days")
    season = et0_module.add_et0_column(season, latitude_deg, elevation_m)
    season["tmean_c"] = (season["tmax_c"] + season["tmin_c"]) / 2.0   # FAO-56 Eq. 9
    return season.reset_index(drop=True)


def optimiser_rule(forecasts: pd.DataFrame, season_dates: list[pd.Timestamp],
                   kc: list[float], taw_mm: float, raw_mm: float,
                   latitude_deg: float, elevation_m: float, max_relative_et_deficit: float,
                   *, min_irrigation_mm: float = 0.0,
                   pop_size: int = opt.DEFAULT_POP_SIZE,
                   n_generations: int = opt.DEFAULT_N_GENERATIONS,
                   seed: int = 1) -> bl.IrrigationRule:
    """An irrigation rule that runs NSGA-II every morning (receding horizon).

    On season day t it uses the forecast issued on day t-1, plans the next 7
    days from today's depletion, and if the plan irrigates today, refills the
    root zone (unless that is below min_irrigation_mm). The plan is the
    least-water one within max_relative_et_deficit; if none qualifies, the
    plan with the smallest deficit is used.
    """
    horizon = 7   # C2 forecasts 7 days ahead (TAF, C2 description)

    def rule(day: int, depletion_mm: float) -> float:
        today = pd.Timestamp(season_dates[day - 1])
        issue_date = (today - pd.DateOffset(days=1)).strftime("%Y-%m-%d")
        scenarios = opt.forecast_scenarios(forecasts, issue_date, latitude_deg, elevation_m)
        # Kc for the next 7 days; after the season ends, keep the last value.
        kc_window = [kc[min(day - 1 + i, len(kc) - 1)] for i in range(horizon)]
        front = opt.optimise_schedule(depletion_mm, scenarios, kc_window, taw_mm, raw_mm,
                                      min_irrigation_mm, pop_size, n_generations, seed)
        try:
            plan = opt.least_water_schedule(front, max_relative_et_deficit)
        except ValueError:
            plan = front.sort_values("relative_et_deficit").iloc[0]
        if plan["day1_irrigate"] and depletion_mm > 0 and depletion_mm >= min_irrigation_mm:
            return depletion_mm          # refill to field capacity (FAO-56 Example 38)
        return 0.0

    return rule


def run_season(rule: bl.IrrigationRule, truth: pd.DataFrame, kc: list[float],
               taw_mm: float, raw_mm: float) -> pd.DataFrame:
    """Simulate one schedule over the season, starting at field capacity."""
    return bl.simulate_with_rule(rule, 0.0, truth["et0_mm_day"].tolist(), kc,
                                 truth["rainfall_mm"].tolist(), taw_mm, raw_mm)


def compare_schedules(results: dict[str, pd.DataFrame], truth: pd.DataFrame,
                      kc: list[float]) -> pd.DataFrame:
    """One row per schedule: water, stress, drainage and climate risk counts."""
    etm_total = sum(k * e for k, e in zip(kc, truth["et0_mm_day"]))   # ETc without stress
    rows = []
    for name, result in results.items():
        row = {"schedule": name}
        row.update(bl.summarise_schedule(result))
        row["relative_et_deficit"] = opt.relative_et_deficit(result["etc_adj_mm"].sum(), etm_total)
        row.update(cr.summarise_risk(truth["tmax_c"].tolist(), truth["tmean_c"].tolist(),
                                     result["ks"].tolist(),
                                     result["deep_percolation_mm"].tolist()))
        rows.append(row)
    return pd.DataFrame(rows)
