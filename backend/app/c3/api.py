"""Stage 12: C3 API endpoints (FastAPI router, mounted at /c3).

Real-data endpoints take the data in the request. Demo endpoints use the
SYNTHETIC sample files and say so in every response ("data": "synthetic"),
so C4 and the dashboard can be built before field data exists.
"""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.c3 import config
from app.c3 import data_loading as dl
from app.c3 import et0 as et0_module
from app.c3 import planner
from app.c3 import weather_sources

router = APIRouter(prefix="/c3", tags=["C3 irrigation"])

SYNTHETIC_NOTE = "SYNTHETIC data and placeholder/proxy values - not a research result"


# ---------------------------------------------------------------------------
# Request models (units in the names)
# ---------------------------------------------------------------------------
class DailyWeather(BaseModel):
    date: str
    tmax_c: float
    tmin_c: float
    rh_mean_pct: float = Field(ge=0, le=100)
    rh_max_pct: float | None = Field(default=None, ge=0, le=100)
    rh_min_pct: float | None = Field(default=None, ge=0, le=100)
    rainfall_mm: float = Field(ge=0)
    wind_speed_2m_ms: float = Field(ge=0)
    solar_radiation_mj_m2_day: float = Field(ge=0)


class Et0Request(BaseModel):
    latitude_deg: float
    elevation_m: float
    days: list[DailyWeather]


class PlanRequest(BaseModel):
    soil_moisture_m3m3: float = Field(ge=0, le=1)
    forecast: list[DailyWeather] = Field(min_length=7, max_length=7)   # today + 6 days
    plot: dict                      # fields of planner.PlotSettings
    kc: list[float] = Field(min_length=7, max_length=7)
    max_relative_et_deficit: float = Field(ge=0, le=1)
    refill_fraction: list[float] | None = None
    min_irrigation_mm: float = 0.0
    water_price_lkr_per_m3: float | None = None
    cost_per_event_lkr: float = 0.0


def _weather_table(days: list[DailyWeather]) -> pd.DataFrame:
    table = pd.DataFrame([d.model_dump() for d in days])
    if table[["rh_max_pct", "rh_min_pct"]].isna().any().any():
        table = table.drop(columns=["rh_max_pct", "rh_min_pct"])   # fall back to Eq. 19
    table["date"] = pd.to_datetime(table["date"])
    return table


def _forecasts_from_days(days: list[DailyWeather]) -> tuple[pd.DataFrame, str]:
    """Daily forecast for today..today+6 -> C3 forecast table issued yesterday."""
    table = _weather_table(days).sort_values("date").reset_index(drop=True)
    issue = table["date"].iloc[0] - pd.DateOffset(days=1)
    table = table.rename(columns={"date": "target_date"})
    table["issue_date"] = issue
    table["lead_day"] = range(1, len(table) + 1)
    return table, issue.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/status")
def status() -> dict:
    """What C3 can do now and which inputs are still placeholders."""
    return {
        "component": "C3 Adaptive Multi-Objective Irrigation Optimisation Engine",
        "crop": config.CROP_NAME,
        "crop_values": "PROXY: FAO-56 bell pepper, no Nai Miris data",
        "field_data": "not yet available; demo endpoints use synthetic data",
    }


@router.post("/et0")
def calculate_et0(request: Et0Request) -> dict:
    """FAO-56 Penman-Monteith ET0 (mm/day) for each day sent."""
    table = et0_module.add_et0_column(_weather_table(request.days), request.latitude_deg,
                                      request.elevation_m)
    return {"et0_mm_day": [round(v, 3) for v in table["et0_mm_day"]],
            "dates": table["date"].dt.strftime("%Y-%m-%d").tolist()}


@router.post("/plan")
def plan(request: PlanRequest) -> dict:
    """Today's irrigation recommendation and the 7-day plan from real inputs."""
    try:
        plot = planner.PlotSettings(**request.plot)
    except TypeError as error:
        raise HTTPException(status_code=422, detail=f"plot settings: {error}")
    forecasts, issue_date = _forecasts_from_days(request.forecast)
    return planner.plan_today(
        request.soil_moisture_m3m3, forecasts, issue_date, plot, request.kc,
        request.max_relative_et_deficit, refill_fraction=request.refill_fraction,
        min_irrigation_mm=request.min_irrigation_mm,
        water_price_lkr_per_m3=request.water_price_lkr_per_m3,
        cost_per_event_lkr=request.cost_per_event_lkr)


def _demo_plot() -> planner.PlotSettings:
    plot = dl.load_plot_config(config.SAMPLE_DATA_DIR / "plot_soil_config_synthetic.json")
    soil = plot["soil"]
    return planner.PlotSettings(
        latitude_deg=plot["plot"]["latitude_deg"], elevation_m=plot["plot"]["elevation_m"],
        field_capacity_m3m3=soil["field_capacity_m3m3"],
        wilting_point_m3m3=soil["wilting_point_m3m3"], root_depth_m=soil["root_depth_m"],
        depletion_fraction_p=config.DEPLETION_FRACTION_P, area_m2=plot["plot"]["area_m2"])


@router.get("/demo/plan")
def demo_plan(issue_date: str = "2025-06-01", soil_moisture_m3m3: float = 0.17,
              max_relative_et_deficit: float = 0.0) -> dict:
    """Recommendation from the SYNTHETIC forecast file (for C4 / dashboard work)."""
    forecasts = dl.load_forecasts(config.SAMPLE_DATA_DIR / "c2_forecast_synthetic_7day.csv")
    try:
        result = planner.plan_today(soil_moisture_m3m3, forecasts, issue_date, _demo_plot(),
                                    [config.KC_MID] * 7, max_relative_et_deficit)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return {"data": "synthetic", "note": SYNTHETIC_NOTE, **result}


LIVE_NOTE = ("REAL live weather forecast (Open-Meteo) at the demo location; soil and crop "
             "values are placeholders / FAO-56 bell pepper proxy - not the test plot")


def _live_forecasts() -> tuple[pd.DataFrame, str]:
    """Today's real forecast at the demo location, as a C3 forecast table
    issued yesterday (so lead day 1 = today, 7 days)."""
    loc = config.DEMO_LOCATION
    daily = weather_sources.fetch_forecast(loc["latitude_deg"], loc["longitude_deg"], days=8)
    issue = (pd.Timestamp(daily["date"].min()) - pd.DateOffset(days=1)).strftime("%Y-%m-%d")
    forecasts = weather_sources.to_c3_forecasts(daily, issue)
    return forecasts[forecasts["lead_day"] <= config.SCHEDULE_DAYS], issue


@router.get("/demo/live-plan")
def demo_live_plan(soil_moisture_m3m3: float = 0.17, max_relative_et_deficit: float = 0.0) -> dict:
    """Today's plan from the LIVE forecast at the demo location (panel demo)."""
    try:
        forecasts, issue_date = _live_forecasts()
    except Exception as error:   # network / service problems
        raise HTTPException(status_code=503, detail=f"weather forecast unavailable: {error}")
    loc = config.DEMO_LOCATION
    plot = _demo_plot()
    plot.latitude_deg, plot.elevation_m = loc["latitude_deg"], loc["elevation_m"]
    result = planner.plan_today(soil_moisture_m3m3, forecasts, issue_date, plot,
                                [config.KC_MID] * config.SCHEDULE_DAYS, max_relative_et_deficit)
    return {"data": "live forecast", "note": LIVE_NOTE, "location": loc, **result}


@router.get("/demo/evaluation-real")
def demo_evaluation_real() -> dict:
    """Season comparison on REAL weather and REAL past forecasts at the demo
    location (run scripts/run_real_weather_evaluation first)."""
    path = Path(config.OUTPUT_DIR) / "evaluation_real_weather_demo_location.csv"
    if not path.exists():
        raise HTTPException(status_code=404,
                            detail="run: python -m app.c3.scripts.run_real_weather_evaluation")
    table = pd.read_csv(path)
    return {"data": "real weather and forecasts", "location": config.DEMO_LOCATION,
            "note": "Real ERA5 weather and real archived forecasts (Open-Meteo); soil and crop "
                    "values are placeholders / proxy - not the test plot",
            "rows": table.round(3).to_dict(orient="records")}


@router.get("/demo/evaluation")
def demo_evaluation() -> dict:
    """Latest synthetic season comparison (run scripts/run_synthetic_evaluation first)."""
    path = Path(config.OUTPUT_DIR) / "evaluation_synthetic.csv"
    if not path.exists():
        raise HTTPException(status_code=404,
                            detail="run: python -m app.c3.scripts.run_synthetic_evaluation")
    table = pd.read_csv(path)
    return {"data": "synthetic", "note": SYNTHETIC_NOTE,
            "rows": table.round(3).to_dict(orient="records")}
