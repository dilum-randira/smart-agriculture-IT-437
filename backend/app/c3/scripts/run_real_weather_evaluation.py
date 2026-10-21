"""Season comparison on REAL weather and REAL past forecasts at the demo location.

    Weather "truth": ERA5 reanalysis (Open-Meteo archive API).
    Forecasts: real forecasts as they were issued 1-7 days ahead
    (Open-Meteo Previous Runs API, archived from January 2024).
    Soil and crop values are still PLACEHOLDERS / the FAO-56 bell pepper
    PROXY, and the location is the demo location (Mahailuppallama), not the
    test plot. State these limitations with any number from this script.

Run from the backend/ folder:
    python -m app.c3.scripts.run_real_weather_evaluation

Downloads are saved in c3_data/processed/ (not in Git) and reused.
"""

from pathlib import Path

import pandas as pd

from app.c3 import baselines as bl
from app.c3 import config
from app.c3 import data_loading as dl
from app.c3 import et0
from app.c3 import evaluation as ev
from app.c3 import optimiser as opt
from app.c3 import stress_classifier as sc
from app.c3 import water_balance as wb
from app.c3 import weather_sources as ws
from app.c3.scripts import run_synthetic_evaluation as synthetic_settings

SEASON_START = "2025-05-01"   # Yala 2025, the dry season when chilli is irrigated
SEASON_DAYS = 90              # TAF: 75-90 day chilli growth cycle (upper end)
TRAINING_YEAR = 2024          # reactive ML is trained on this year only
HORIZON = 7


def cached(path: Path, download) -> pd.DataFrame:
    """Read a saved download, or download and save it. Date columns are restored."""
    if path.exists():
        table = pd.read_csv(path)
        for col in ("date", "issue_date", "target_date"):
            if col in table:
                table[col] = pd.to_datetime(table[col])
        return table
    table = download()
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return table


def main(season_start: str = SEASON_START, season_days: int = SEASON_DAYS,
         pop_size: int = opt.DEFAULT_POP_SIZE, n_generations: int = opt.DEFAULT_N_GENERATIONS,
         data_dir: Path = config.PROCESSED_DATA_DIR, output_dir: Path = config.OUTPUT_DIR,
         get=None) -> pd.DataFrame:
    loc = config.DEMO_LOCATION
    lat, lon, elev = loc["latitude_deg"], loc["longitude_deg"], loc["elevation_m"]
    start = pd.Timestamp(season_start)
    end = start + pd.DateOffset(days=season_days - 1)
    last_target = end + pd.DateOffset(days=HORIZON)
    fmt = lambda t: t.strftime("%Y-%m-%d")
    tag = f"demo_location_{fmt(start)}_{season_days}d"

    weather = cached(Path(data_dir) / f"era5_daily_{tag}.csv",
                     lambda: ws.fetch_history(lat, lon, fmt(start), fmt(last_target), get=get))
    forecasts = cached(Path(data_dir) / f"previous_runs_forecasts_{tag}.csv",
                       lambda: ws.fetch_previous_runs(lat, lon, fmt(start), fmt(last_target), get=get))
    history = cached(Path(data_dir) / f"era5_daily_demo_location_{TRAINING_YEAR}.csv",
                     lambda: ws.fetch_history(lat, lon, f"{TRAINING_YEAR}-01-01",
                                              f"{TRAINING_YEAR}-12-31", get=get))

    plot = dl.load_plot_config(config.SAMPLE_DATA_DIR / "plot_soil_config_synthetic.json")
    soil = plot["soil"]                                   # PLACEHOLDER soil values
    taw = wb.total_available_water_mm(soil["field_capacity_m3m3"], soil["wilting_point_m3m3"],
                                      soil["root_depth_m"])
    raw = wb.readily_available_water_mm(taw, config.DEPLETION_FRACTION_P)
    kc = [config.KC_MID] * season_days                    # PROXY: FAO-56 bell pepper Kc mid

    truth = ev.season_truth(weather, fmt(start), season_days, lat, elev)
    dates = truth["date"].tolist()

    rules = {"no irrigation": bl.no_irrigation_rule,
             "fixed threshold (RAW)": bl.fixed_threshold_rule(raw)}
    for early in synthetic_settings.DOA_EARLY_INTERVALS:
        for end_day in synthetic_settings.DOA_EARLY_END_DAYS:
            days = bl.doa_irrigation_days(season_days, early, synthetic_settings.DOA_LATE_INTERVAL,
                                          end_day)
            rules[f"DoA every {early}d, weekly after day {end_day}"] = bl.doa_schedule_rule(days)

    training = et0.add_et0_column(history, lat, elev)
    training_days = sc.build_training_days(
        training, bl.doa_schedule_rule(bl.doa_irrigation_days(len(training), 5, 7, 1)),
        [config.KC_MID] * len(training), taw, raw, soil["field_capacity_m3m3"], soil["root_depth_m"])
    model = sc.train_stress_classifier(training_days)
    rules["reactive ML (Random Forest)"] = sc.reactive_ml_rule(
        model, truth, soil["field_capacity_m3m3"], soil["root_depth_m"])

    settings = dict(pop_size=pop_size, n_generations=n_generations)
    for deficit in synthetic_settings.ALLOWED_DEFICITS:
        rules[f"NSGA-II real forecasts, deficit {deficit:.2f}"] = ev.optimiser_rule(
            forecasts, dates, kc, taw, raw, lat, elev, deficit, **settings)
    full_truth = ev.season_truth(weather, fmt(start), season_days + HORIZON, lat, elev)
    rules["NSGA-II PERFECT forecast, deficit 0.00 (upper bound)"] = ev.optimiser_rule(
        ev.perfect_forecasts(full_truth.drop(columns=["et0_mm_day", "tmean_c"]), HORIZON),
        dates, kc, taw, raw, lat, elev, 0.0, **settings)

    results = {name: ev.run_season(rule, truth, kc, taw, raw) for name, rule in rules.items()}
    table = ev.compare_schedules(results, truth, kc)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "evaluation_real_weather_demo_location.csv"
    table.to_csv(out_file, index=False)

    print("REAL WEATHER + REAL PAST FORECASTS at the demo location; "
          "soil and crop values are placeholders / proxy")
    print(f"{loc['name']}, {season_days} days from {fmt(start)}, season rain "
          f"{truth['rainfall_mm'].sum():.0f} mm, TAW {taw:.0f} mm, RAW {raw:.0f} mm, "
          f"Kc {config.KC_MID} (proxy)")
    print(table.round(3).to_string(index=False))
    print(f"Saved to {out_file}")
    return table


if __name__ == "__main__":
    main()
