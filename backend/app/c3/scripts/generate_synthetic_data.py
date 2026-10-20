"""Generate SYNTHETIC development datasets for C3.

Why this exists
---------------
C1 (sensor data) and C2 (forecasts) are not ready yet. These files let C3
code be written and tested now. They are made up by this script.

    THESE ARE NOT REAL MEASUREMENTS. NEVER REPORT THEM AS FIELD DATA.
    Replace them with C1/C2 data and real historical weather when available.

The weather is only loosely shaped like a Sri Lankan dry-zone year (wet
Maha season Oct-Jan, drier and windier Yala season May-Sep). It is NOT
real climatology.

Run from the backend/ folder:
    python -m app.c3.scripts.generate_synthetic_data

The same seed always produces the same files.

How constants are labelled in this file
---------------------------------------
- A source (e.g. "FAO-56 Eq. 82") means the number comes from that reference.
- "INVENTED - synthetic only" means the number was made up only to shape the
  fake data. It must never be used in a real C3 calculation.
- "PLACEHOLDER" means C3 calculations WILL use this kind of value later, so a
  real source (soil test, plot survey, published table) is needed before
  Stage 4. Until then the value is only for testing code.
"""

import json
import math

import numpy as np
import pandas as pd

from app.c3 import config

SEED = 437  # project number, so everyone gets identical files
OUT = config.SAMPLE_DATA_DIR

# Placeholder site. REPLACE with the real test plot when it is chosen.
LATITUDE_DEG = 7.9      # PLACEHOLDER: roughly central Sri Lanka, not the real plot
ELEVATION_M = 150.0     # PLACEHOLDER: not the real plot

WEATHER_START, WEATHER_END = "2024-01-01", "2025-12-31"
SENSOR_START, SENSOR_DAYS = "2025-05-01", 90   # one mock dry-season crop cycle


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def extraterrestrial_radiation(day_of_year: int, latitude_deg: float) -> float:
    """Ra in MJ/m2/day, FAO-56 Eq. 21 (with Eq. 22-25).

    Used here only to give the synthetic solar radiation a realistic size.
    """
    phi = math.radians(latitude_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)            # Eq. 23
    delta = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)     # Eq. 24
    ws = math.acos(-math.tan(phi) * math.tan(delta))                      # Eq. 25
    gsc = 0.0820                                # MJ/m2/min, solar constant, FAO-56 Eq. 21
    return (24 * 60 / math.pi) * gsc * dr * (
        ws * math.sin(phi) * math.sin(delta)
        + math.cos(phi) * math.cos(delta) * math.sin(ws)
    )


def seasonal(month: int, values_by_month: list) -> float:
    """Pick this month's value from a 12-item list (January first)."""
    return values_by_month[month - 1]


# INVENTED - synthetic only. Monthly patterns loosely shaped like a dry-zone
# year. Not measured climatology; no source.
RAIN_DAY_CHANCE = [0.25, 0.12, 0.15, 0.35, 0.20, 0.08, 0.08, 0.10, 0.15, 0.45, 0.55, 0.45]
TMAX_MEAN_C     = [30.0, 31.5, 33.5, 34.0, 34.0, 33.0, 33.0, 33.0, 33.0, 31.5, 30.0, 29.5]
TMIN_MEAN_C     = [21.5, 21.5, 22.5, 23.5, 24.5, 24.5, 24.0, 24.0, 23.5, 23.0, 22.5, 22.0]
RH_MEAN_PCT     = [80.0, 74.0, 70.0, 74.0, 70.0, 66.0, 66.0, 66.0, 70.0, 80.0, 85.0, 84.0]
WIND_2M_MS      = [1.8, 1.6, 1.3, 1.2, 2.5, 3.8, 4.0, 3.8, 3.0, 1.8, 1.6, 1.8]


# ---------------------------------------------------------------------------
# 1. Daily weather (stand-in for real historical weather, e.g. ERA5)
# ---------------------------------------------------------------------------
def make_daily_weather(rng: np.random.Generator) -> pd.DataFrame:
    dates = pd.date_range(WEATHER_START, WEATHER_END, freq="D")
    rows = []
    was_wet = False
    for day in dates:
        m = day.month
        # Rain: wet days are more likely after a wet day (simple persistence).
        # INVENTED - synthetic only: the 1.6 / 0.9 persistence factors, the
        # gamma(0.8, 18) rain amounts, the 1.8 degC wet-day cooling, the
        # 4 degC minimum daily range, the +8 % wet-day humidity, the noise
        # sizes and the 0.3 m/s wind floor below.
        chance = seasonal(m, RAIN_DAY_CHANCE)
        chance = min(0.9, chance * 1.6) if was_wet else chance
        wet = rng.random() < chance
        rain = float(rng.gamma(shape=0.8, scale=18.0)) if wet else 0.0
        was_wet = wet

        tmax = seasonal(m, TMAX_MEAN_C) + rng.normal(0, 1.0) - (1.8 if wet else 0.0)
        tmin = seasonal(m, TMIN_MEAN_C) + rng.normal(0, 0.7)
        tmin = min(tmin, tmax - 4.0)  # keep a sensible daily range
        rh = seasonal(m, RH_MEAN_PCT) + rng.normal(0, 4.0) + (8.0 if wet else 0.0)
        wind = max(0.3, seasonal(m, WIND_2M_MS) + rng.normal(0, 0.5))

        ra = extraterrestrial_radiation(day.dayofyear, LATITUDE_DEG)
        # Rs/Ra fraction. INVENTED - synthetic only, but kept below the
        # clear-sky limit of about 0.75 x Ra (FAO-56 Eq. 35-37, as + bs = 0.75).
        sky = rng.uniform(0.35, 0.50) if wet else rng.uniform(0.50, 0.70)
        rs = ra * sky

        rows.append({
            "date": day.date().isoformat(),
            "tmax_c": round(tmax, 1),
            "tmin_c": round(tmin, 1),
            "rh_mean_pct": round(float(np.clip(rh, 40, 98)), 1),  # 40-98 %: INVENTED - synthetic only
            "rainfall_mm": round(rain, 1),
            "wind_speed_2m_ms": round(wind, 2),
            "solar_radiation_mj_m2_day": round(rs, 2),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. Mock C1 sensor stream (15-minute readings)
# ---------------------------------------------------------------------------
# Sum of the daylight "sun" factor over the 96 quarter-hours of one day.
SUN_FACTOR_SUM_PER_DAY = sum(
    max(0.0, math.sin(math.pi * (q / 4 - 6) / 12)) for q in range(96) if 6 <= q / 4 <= 18
)


def make_sensor_stream(weather: pd.DataFrame, plot: dict, rng: np.random.Generator) -> pd.DataFrame:
    """Simple 'bucket' soil model driven by the synthetic weather.

    Purpose: give C3 a realistic-looking soil moisture signal with noise,
    gaps and spikes. The crop water use here is a rough guess, not FAO-56.
    """
    soil = plot["soil"]
    fc, wp, root_m = soil["field_capacity_m3m3"], soil["wilting_point_m3m3"], soil["root_depth_m"]
    taw_mm = 1000 * (fc - wp) * root_m      # total available water in the root zone, FAO-56 Eq. 82

    w = weather.set_index("date")
    start = pd.Timestamp(SENSOR_START)
    stamps = pd.date_range(start, periods=SENSOR_DAYS * 96, freq="15min")

    depletion_mm = 0.2 * taw_mm             # start a bit below field capacity (INVENTED - synthetic only)
    soil_temp = 27.0                        # degC, starting value (INVENTED - synthetic only)
    rows = []
    for ts in stamps:
        d = w.loc[ts.date().isoformat()]
        hour = ts.hour + ts.minute / 60

        # Air temperature: coolest ~06:00, hottest ~14:00.
        # INVENTED - synthetic only: the daily curve shape and the +/-15 %
        # humidity swing.
        temp_wave = (1 - math.cos(math.pi * (hour - 6) / 8)) / 2 if 6 <= hour <= 14 else \
                    (1 + math.cos(math.pi * ((hour - 14) % 24) / 16)) / 2
        air_t = d.tmin_c + (d.tmax_c - d.tmin_c) * temp_wave
        air_rh = float(np.clip(d.rh_mean_pct + 15 * (0.5 - temp_wave) * 2, 35, 100))

        # Light: daylight 06:00-18:00 (INVENTED - synthetic only).
        # 65535 lux = BH1750 maximum reading (ROHM BH1750FVI datasheet).
        # 5200 lux per MJ/m2/day: INVENTED - synthetic only, no source. It just
        # gives midday readings of a realistic size.
        sun = max(0.0, math.sin(math.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0.0
        lux = min(65535.0, sun * d.solar_radiation_mj_m2_day * 5200 * rng.uniform(0.7, 1.0))

        # Rain: daily total falls as an afternoon shower 14:00-17:00
        # (INVENTED - synthetic only). 12 steps = 3 hours x 4 per hour.
        rain_step = d.rainfall_mm / 12 if 14 <= hour < 17 else 0.0

        # Mock farmer irrigates 07:00 when the soil looks dry (NOT a C3 baseline).
        # INVENTED - synthetic only: the 45 % of TAW trigger and 90 % refill.
        irrigation_step = 0.0
        if ts.hour == 7 and ts.minute == 0 and depletion_mm > 0.45 * taw_mm:
            irrigation_step = round(depletion_mm * 0.9, 1)

        # Crop water use: rough daily guess spread over daylight hours.
        # INVENTED - synthetic only. The 0.0023 and 2.2 are NOT the Hargreaves
        # equation (FAO-56 Eq. 52) and this is NOT FAO-56 ET. Never reuse it.
        daily_use_mm = 0.0023 * (d.tmax_c + d.tmin_c) / 2 * d.solar_radiation_mj_m2_day * 2.2
        et_step = daily_use_mm * sun / SUN_FACTOR_SUM_PER_DAY  # spreads the daily total
        # Water stress reduction, same form as Ks in FAO-56 Eq. 84 with
        # depletion fraction p = 0.5. p = 0.5 is a PLACEHOLDER: the real p
        # depends on the crop (FAO-56 Table 22).
        stress_factor =1.0 if depletion_mm < 0.5 * taw_mm else max(0.0, (taw_mm - depletion_mm) / (0.5 * taw_mm))
        depletion_mm += et_step * stress_factor - rain_step - irrigation_step
        depletion_mm = float(np.clip(depletion_mm, 0.0, taw_mm))   # extra water drains away

        vwc = fc - depletion_mm / (1000 * root_m)   # m3/m3 (1000 mm per m)
        # Soil lags behind air. INVENTED - synthetic only: 2.0 degC offset, 0.03 lag.
        soil_temp += (air_t - 2.0 - soil_temp) * 0.03

        rows.append({
            "timestamp": ts.isoformat(),
            "sensor_id": "synthetic-node-01",
            "soil_moisture_pct": round(100 * vwc + rng.normal(0, 0.5), 2),
            "soil_temp_c": round(soil_temp + rng.normal(0, 0.2), 2),
            "air_temp_c": round(air_t + rng.normal(0, 0.3), 2),
            "air_humidity_pct": round(float(np.clip(air_rh + rng.normal(0, 1.5), 0, 100)), 1),
            "light_lux": round(lux, 0),
            "rainfall_mm": round(rain_step, 2),
            "irrigation_logged_mm": irrigation_step,
        })
    df = pd.DataFrame(rows)

    # Real sensors fail: add outages (blank values) and a few bad spikes.
    # INVENTED - synthetic only: number, length and size of the faults.
    sensor_cols = ["soil_moisture_pct", "soil_temp_c", "air_temp_c", "air_humidity_pct", "light_lux"]
    for _ in range(4):
        start_i = int(rng.integers(0, len(df) - 40))
        df.loc[start_i:start_i + int(rng.integers(8, 32)), sensor_cols] = np.nan
    for i in rng.integers(0, len(df), 6):
        df.loc[i, "soil_moisture_pct"] = round(float(rng.choice([0.0, 99.9, 150.0])), 1)
    return df


# ---------------------------------------------------------------------------
# 3. Mock C2 forecasts (7 days ahead, issued every day)
# ---------------------------------------------------------------------------
def make_forecasts(weather: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """'Forecast' = synthetic truth + error that grows with lead time.

    The error sizes are invented. They say nothing about C2's real accuracy.
    INVENTED - synthetic only: every error size, miss/false-alarm rate,
    clipping limit and the rain p90 formula in this function.
    """
    w = weather.reset_index(drop=True)
    rows = []
    for i in range(len(w) - 7):
        issue_date = w.loc[i, "date"]
        for lead in range(1, 8):
            truth = w.loc[i + lead]
            t_sd = 0.5 + 0.25 * lead                     # degC
            rh_sd = 3.0 + 1.0 * lead                      # %
            tmax = truth.tmax_c + rng.normal(0, t_sd)
            tmin = min(truth.tmin_c + rng.normal(0, t_sd), tmax - 2.0)
            rh = float(np.clip(truth.rh_mean_pct + rng.normal(0, rh_sd), 30, 100))

            # Rain is hard to forecast: missed showers and false alarms get
            # more likely further ahead.
            miss_or_false = 0.10 + 0.05 * lead
            if truth.rainfall_mm > 0 and rng.random() < miss_or_false:
                rain = 0.0
            elif truth.rainfall_mm == 0 and rng.random() < miss_or_false / 2:
                rain = float(rng.gamma(0.8, 8.0))
            else:
                rain = truth.rainfall_mm * float(rng.lognormal(0, 0.3 + 0.08 * lead))

            rows.append({
                "issue_date": issue_date,
                "target_date": truth.date,
                "lead_day": lead,
                "tmax_c": round(tmax, 1),
                # 1.28 = z-score of the 90th percentile of a normal distribution
                # (standard statistics; exact value 1.2816).
                "tmax_c_p10": round(tmax - 1.28 * t_sd, 1),
                "tmax_c_p90": round(tmax + 1.28 * t_sd, 1),
                "tmin_c": round(tmin, 1),
                "rh_mean_pct": round(rh, 1),
                "rainfall_mm": round(rain, 1),
                "rainfall_mm_p90": round(rain * 2.0 + 2.0 * lead, 1),
                "wind_speed_2m_ms": round(max(0.3, truth.wind_speed_2m_ms + rng.normal(0, 0.3 + 0.1 * lead)), 2),
                "solar_radiation_mj_m2_day": round(max(5.0, truth.solar_radiation_mj_m2_day + rng.normal(0, 1.0 + 0.4 * lead)), 2),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Plot and soil settings (placeholders)
# ---------------------------------------------------------------------------
def make_plot_config() -> dict:
    """Plot and soil settings. Every value is a PLACEHOLDER (see module docstring).

    - area_m2 50: PLACEHOLDER, not the real plot.
    - irrigation_efficiency 0.85: PLACEHOLDER, assumed drip, no source yet.
    - field_capacity 0.22 / wilting_point 0.10 m3/m3: PLACEHOLDER, chosen
      inside the sandy loam ranges of FAO-56 Table 19. Replace with a soil test.
    - root_depth_m 0.5: PLACEHOLDER. Real value depends on the crop
      (FAO-56 Table 22), and the crop is not chosen yet.
    """
    return {
        "_status": "SYNTHETIC PLACEHOLDERS - replace every value with real plot data",
        "plot": {
            "latitude_deg": LATITUDE_DEG,
            "elevation_m": ELEVATION_M,
            "area_m2": 50.0,
            "transplant_date": SENSOR_START,
            "irrigation_efficiency": 0.85,
            "water_cost_lkr_per_m3": None,
        },
        "soil": {
            "texture": "sandy loam (assumed)",
            "field_capacity_m3m3": 0.22,
            "wilting_point_m3m3": 0.10,
            "root_depth_m": 0.5,
        },
        "_notes": {
            "latitude_deg / elevation_m": "Placeholder. Use the real test plot.",
            "irrigation_efficiency": "Assumed drip system. Confirm the real method.",
            "water_cost_lkr_per_m3": "Unknown - left empty on purpose. Find the real cost.",
            "soil": "Typical textbook-range sandy loam values. Replace with a soil test "
                    "or published values for the plot's soil.",
        },
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    plot = make_plot_config()
    weather = make_daily_weather(rng)
    sensors = make_sensor_stream(weather, plot, rng)
    forecasts = make_forecasts(weather, rng)

    weather.to_csv(OUT / "weather_synthetic_daily.csv", index=False)
    sensors.to_csv(OUT / "c1_sensor_synthetic_15min.csv", index=False)
    forecasts.to_csv(OUT / "c2_forecast_synthetic_7day.csv", index=False)
    with open(OUT / "plot_soil_config_synthetic.json", "w", encoding="utf-8") as f:
        json.dump(plot, f, indent=2)

    print(f"Wrote SYNTHETIC files to {OUT}")
    print(f"  weather:   {len(weather):>6} days")
    print(f"  sensors:   {len(sensors):>6} rows (15-minute)")
    print(f"  forecasts: {len(forecasts):>6} rows (issue date x 7 lead days)")


if __name__ == "__main__":
    main()
