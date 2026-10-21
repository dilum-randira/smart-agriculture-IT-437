"""Tune NSGA-II population size and generations on the SYNTHETIC forecasts.

With 7 yes/no irrigation decisions there are only 2^7 = 128 plans, so the
exact Pareto front can be found by trying them all. For each test case this
script checks how much of that exact front NSGA-II finds, for a grid of
settings, and picks the cheapest setting that finds 100 % in every case.

(Trying all plans would also work at 7 days. NSGA-II is kept because the
search space grows quickly with longer horizons or partial-refill amounts.)

Run from the backend/ folder:
    python -m app.c3.scripts.tune_nsga2
"""

import pandas as pd

from app.c3 import config
from app.c3 import data_loading as dl
from app.c3 import optimiser as opt
from app.c3 import water_balance as wb

POP_SIZES = [10, 20, 40, 60]
GENERATIONS = [10, 20, 40, 80]
CASE_DAYS = 30            # test cases start from this many forecast issue days
CASE_EVERY_DAYS = 3       # spacing between the forecast issue days


def front_recovery(found: pd.DataFrame, exact_front: pd.DataFrame) -> float:
    """Fraction (0-1) of the exact Pareto front's objective vectors NSGA-II found."""
    key = lambda df: set(map(tuple, df[opt.OBJECTIVES].round(9).to_numpy()))
    exact = key(exact_front)
    return len(exact & key(opt.pareto_front(found))) / len(exact)


def test_cases(season_start: str, taw: float, raw: float, lat: float, elev: float,
               forecasts: pd.DataFrame) -> list[tuple]:
    """(scenarios, start depletion) pairs: several forecast days x soil states."""
    issue_dates = pd.date_range(season_start, periods=CASE_DAYS, freq=f"{CASE_EVERY_DAYS}D")
    start_depletions = [0.0, raw / 2, raw, (raw + taw) / 2]   # full, half RAW, at RAW, stressed
    cases = []
    for issue in issue_dates:
        scenarios = opt.forecast_scenarios(forecasts, issue.strftime("%Y-%m-%d"), lat, elev)
        for depletion in start_depletions:
            cases.append((scenarios, depletion))
    return cases


def main(pop_sizes: list[int] = POP_SIZES, generations: list[int] = GENERATIONS,
         max_cases: int | None = None) -> pd.DataFrame:
    sample = config.SAMPLE_DATA_DIR
    plot = dl.load_plot_config(sample / "plot_soil_config_synthetic.json")
    forecasts = dl.load_forecasts(sample / "c2_forecast_synthetic_7day.csv")
    soil = plot["soil"]
    taw = wb.total_available_water_mm(soil["field_capacity_m3m3"], soil["wilting_point_m3m3"],
                                      soil["root_depth_m"])
    raw = wb.readily_available_water_mm(taw, config.DEPLETION_FRACTION_P)
    kc = [config.KC_MID] * 7   # PROXY: FAO-56 bell pepper Kc mid
    cases = test_cases(plot["plot"]["transplant_date"], taw, raw,
                       plot["plot"]["latitude_deg"], plot["plot"]["elevation_m"], forecasts)
    cases = cases[:max_cases] if max_cases else cases

    exact_fronts = [opt.pareto_front(opt.all_schedules(d, s, kc, taw, raw)) for s, d in cases]
    rows = []
    for pop in pop_sizes:
        for gen in generations:
            scores = [front_recovery(opt.optimise_schedule(d, s, kc, taw, raw,
                                                           pop_size=pop, n_generations=gen),
                                     exact)
                      for (s, d), exact in zip(cases, exact_fronts)]
            rows.append({"pop_size": pop, "n_generations": gen, "evaluations": pop * gen,
                         "mean_recovery": sum(scores) / len(scores),
                         "worst_recovery": min(scores)})
    table = pd.DataFrame(rows).sort_values("evaluations").reset_index(drop=True)

    print(f"SYNTHETIC forecasts, {len(cases)} test cases")
    print(table.round(3).to_string(index=False))
    full = table[table["worst_recovery"] == 1.0]
    if full.empty:
        print("No setting found the full front in every case.")
    else:
        best = full.iloc[0]
        print(f"Cheapest setting with 100 % recovery in every case: "
              f"pop_size={int(best.pop_size)}, n_generations={int(best.n_generations)}")
    return table


if __name__ == "__main__":
    main()
