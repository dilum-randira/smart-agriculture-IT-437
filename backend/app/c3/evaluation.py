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
                   refill_fraction_by_day: list[float] | None = None,
                   worst_case_no_rain: bool = True,
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
        if not worst_case_no_rain:
            scenarios = scenarios[:1]          # trust the forecast (no "rain fails" case)
        # Real archives can miss a lead day: plan over the days that exist.
        days_available = min(horizon, len(scenarios[0].et0_mm_day))
        scenarios = [opt.WeatherScenario(s.name, s.et0_mm_day[:days_available],
                                         s.rain_mm[:days_available], s.tmean_c[:days_available])
                     for s in scenarios]
        # Kc for the planned days; after the season ends, keep the last value.
        window = lambda values: [values[min(day - 1 + i, len(values) - 1)]
                                 for i in range(days_available)]
        kc_window = window(kc)
        refill_window = window(refill_fraction_by_day) if refill_fraction_by_day else None
        front = opt.optimise_schedule(depletion_mm, scenarios, kc_window, taw_mm, raw_mm,
                                      min_irrigation_mm, pop_size, n_generations, seed,
                                      refill_fraction=refill_window)
        try:
            plan = opt.least_water_schedule(front, max_relative_et_deficit)
        except ValueError:
            plan = front.sort_values("relative_et_deficit").iloc[0]
        amount = (refill_window[0] if refill_window else 1.0) * depletion_mm
        if plan["day1_irrigate"] and amount > 0 and amount >= min_irrigation_mm:
            return amount        # refill (or partial refill) of today's depletion
        return 0.0

    return rule


def perfect_forecasts(truth: pd.DataFrame, horizon: int = 7) -> pd.DataFrame:
    """A 'forecast' that is exactly the true weather: the upper bound on how
    much forecasts can help. truth: daily weather (date + weather columns).
    Every true day becomes the forecast for lead days 1..horizon, issued
    `lead` days before it."""
    weather = truth.drop(columns=[c for c in ("et0_mm_day", "tmean_c") if c in truth])
    parts = []
    for lead in range(1, horizon + 1):
        part = weather.rename(columns={"date": "target_date"})
        part["lead_day"] = lead
        part["issue_date"] = part["target_date"] - pd.to_timedelta(lead, unit="D")
        parts.append(part)
    return pd.concat(parts, ignore_index=True).sort_values(["issue_date", "lead_day"]) \
        .reset_index(drop=True)


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
