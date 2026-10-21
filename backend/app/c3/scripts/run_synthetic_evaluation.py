"""Run the Stage 11 comparison on the SYNTHETIC sample files.

    THE OUTPUT IS NOT A RESEARCH RESULT. The weather, forecasts, soil and
    crop values are synthetic, placeholders or proxies. This run only shows
    that the evaluation pipeline works end to end.

Run from the backend/ folder:
    python -m app.c3.scripts.run_synthetic_evaluation

Schedules compared:
- no irrigation (reference)
- fixed threshold at RAW (FAO-56 Example 38)
- DoA interval schedule: early interval 4 and 5 days, weekly later (HORDI);
  early stage ending on day 21, 30 or 45 (sensitivity test: HORDI does not
  say when "early" ends)
- NSGA-II optimiser with allowed ET deficit 0, 0.05 and 0.10 (sensitivity
  test: the allowed deficit is a farmer / C4 choice)
"""

from pathlib import Path

import pandas as pd

from app.c3 import baselines as bl
from app.c3 import config
from app.c3 import data_loading as dl
from app.c3 import evaluation as ev
from app.c3 import optimiser as opt
from app.c3 import water_balance as wb

SEASON_DAYS = 90                 # TAF: 75-90 day chilli growth cycle (upper end)
DOA_EARLY_INTERVALS = [4, 5]     # days, HORDI: "4-5 day intervals at early stages"
DOA_LATE_INTERVAL = 7            # days, HORDI: "1 week interval at latter stages"
DOA_EARLY_END_DAYS = [21, 30, 45]  # sensitivity test, NOT from a source
ALLOWED_DEFICITS = [0.0, 0.05, 0.10]  # sensitivity test, NOT agronomic constants
MIN_IRRIGATION_MM = 0.0          # off: needs a sourced value for the irrigation method


def main(season_days: int = SEASON_DAYS, pop_size: int = opt.DEFAULT_POP_SIZE,
         n_generations: int = opt.DEFAULT_N_GENERATIONS,
         output_dir: Path = config.OUTPUT_DIR) -> pd.DataFrame:
    sample = config.SAMPLE_DATA_DIR
    plot = dl.load_plot_config(sample / "plot_soil_config_synthetic.json")
    weather = dl.load_weather(sample / "weather_synthetic_daily.csv")
    forecasts = dl.load_forecasts(sample / "c2_forecast_synthetic_7day.csv")

    lat, elev = plot["plot"]["latitude_deg"], plot["plot"]["elevation_m"]
    soil = plot["soil"]
    taw = wb.total_available_water_mm(soil["field_capacity_m3m3"], soil["wilting_point_m3m3"],
                                      soil["root_depth_m"])
    raw = wb.readily_available_water_mm(taw, config.DEPLETION_FRACTION_P)
    kc = [config.KC_MID] * season_days   # PROXY: constant FAO-56 bell pepper Kc mid

    truth = ev.season_truth(weather, plot["plot"]["transplant_date"], season_days, lat, elev)
    dates = truth["date"].tolist()

    rules = {
        "no irrigation": bl.no_irrigation_rule,
        "fixed threshold (RAW)": bl.fixed_threshold_rule(raw),
    }
    for early in DOA_EARLY_INTERVALS:
        for end_day in DOA_EARLY_END_DAYS:
            days = bl.doa_irrigation_days(season_days, early, DOA_LATE_INTERVAL, end_day)
            rules[f"DoA every {early}d, weekly after day {end_day}"] = bl.doa_schedule_rule(days)
    for deficit in ALLOWED_DEFICITS:
        rules[f"NSGA-II, allowed deficit {deficit:.2f}"] = ev.optimiser_rule(
            forecasts, dates, kc, taw, raw, lat, elev, deficit,
            min_irrigation_mm=MIN_IRRIGATION_MM, pop_size=pop_size, n_generations=n_generations)

    results = {name: ev.run_season(rule, truth, kc, taw, raw) for name, rule in rules.items()}
    table = ev.compare_schedules(results, truth, kc)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "evaluation_synthetic.csv"
    table.to_csv(out_file, index=False)

    print("SYNTHETIC DATA - NOT A RESULT")
    print(f"{season_days} days from {plot['plot']['transplant_date']}, TAW {taw:.0f} mm, "
          f"RAW {raw:.0f} mm, Kc {config.KC_MID} (proxy)")
    print(table.round(3).to_string(index=False))
    print(f"Saved to {out_file}")
    return table


if __name__ == "__main__":
    main()
