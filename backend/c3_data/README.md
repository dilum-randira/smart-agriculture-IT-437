# C3 data folder

| Folder | What goes here | In Git? |
| --- | --- | --- |
| `raw/` | Files exactly as downloaded or received (never edit them) | No |
| `processed/` | Cleaned files that C3 code reads | No |
| `sample/` | Small, clearly labelled made-up files for development and tests | Yes |
| `outputs/` | Schedules, charts and experiment results | No |

Every dataset added here must be recorded below with its source, date
downloaded, units and licence. Synthetic data must have `synthetic` in its
file name and must never be reported as field data.

## Dataset log

| File | Source | Date obtained | Units / notes |
| --- | --- | --- | --- |
| processed/era5_daily_demo_location_2025-05-01_90d.csv | ERA5 reanalysis via Open-Meteo archive API (archive-api.open-meteo.com), Mahailuppallama demo location 8.0974 N 80.4465 E; "Generated using Copernicus Climate Change Service information" | 2026-10-21 | Daily; degC, %, mm, wind converted 10 m -> 2 m (FAO-56 Eq. 47), MJ/m2/day. Real weather, demo location (not the test plot) |
| processed/era5_daily_demo_location_2024.csv | Same source and location, full year 2024 | 2026-10-21 | As above; used only to train the reactive ML baseline |
| processed/previous_runs_forecasts_demo_location_2025-05-01_90d.csv | Open-Meteo Previous Runs API (previous-runs-api.open-meteo.com), "best match" models, forecasts as issued 1-7 days ahead | 2026-10-21 | Hourly -> daily (max/min from hourly values, radiation sum W/m2 x 3600 s -> MJ/m2/day). Real past forecasts, demo location |

Regenerate with `python -m app.c3.scripts.run_real_weather_evaluation`
(delete the files first to download again). Open-Meteo is free for
non-commercial use; cite Open-Meteo and its sources.
