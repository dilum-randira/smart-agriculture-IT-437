# C3 sample data — ALL SYNTHETIC

> **Every file in this folder is made up by
> `app/c3/scripts/generate_synthetic_data.py` (seed 437).
> None of it is measured. Never report it as field data or use it as
> evidence in the thesis. It exists only so C3 code can be built and
> tested before C1 sensor data and C2 forecasts are available.**

Regenerate (from `backend/`): `python -m app.c3.scripts.generate_synthetic_data`

| File | Stands in for | Replace with |
| --- | --- | --- |
| `weather_synthetic_daily.csv` | 2 years of daily weather (2024–2025) | Real historical weather (Open-Meteo archive / ERA5) for the test plot |
| `c1_sensor_synthetic_15min.csv` | 90 days of C1 ESP32 readings every 15 min | C1's real data / REST API (agree column names with C1) |
| `c2_forecast_synthetic_7day.csv` | C2's 7-day forecasts, issued daily | C2's real forecast output (agree format with C2) |
| `plot_soil_config_synthetic.json` | Plot and soil settings | Real plot location, soil test, irrigation method, water cost |

## How each file was made

**Weather.** Daily values with invented monthly patterns loosely shaped
like a Sri Lankan dry-zone year (wetter Oct–Jan, drier and windier
Jun–Aug). Rain uses simple wet-day persistence. Solar radiation is a
fraction of extraterrestrial radiation (FAO-56 Eq. 21) at a placeholder
latitude. It is **not** real climatology.

**C1 sensors.** A simple soil "bucket" driven by the synthetic weather,
with a mock farmer who irrigates at 07:00 when the soil looks dry (this is
not one of the C3 baselines). Deliberately includes realistic faults:
sensor noise, 4 outages (blank cells), 6 impossible soil-moisture spikes
(0, 99.9, 150 %), and light readings capped at 65 535 lux (BH1750 limit).
`irrigation_logged_mm` represents a farmer's log, not a sensor.
pH, EC and leaf wetness are left out because C3 does not use them.

**C2 forecasts.** Synthetic weather plus random error that grows with
lead time (1–7 days), plus missed and false rain events. p10/p90 columns
are crude ranges. The error sizes are invented and say **nothing** about
C2's real accuracy.

**Plot/soil config.** Placeholder values (assumed sandy loam, assumed drip
efficiency 0.85). Water cost is deliberately empty because it is unknown.

## Column units

Weather and forecasts: `tmax_c`, `tmin_c` (°C), `rh_mean_pct` (%),
`rainfall_mm` (mm/day), `wind_speed_2m_ms` (m/s at 2 m),
`solar_radiation_mj_m2_day` (MJ/m²/day).
Sensors: `soil_moisture_pct` (volumetric %, divide by 100 for m³/m³),
temperatures °C, `air_humidity_pct` %, `light_lux` lux, `rainfall_mm`
mm per 15 min.
