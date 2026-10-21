"""Tests for app/c3/api.py (Stage 12) using FastAPI's TestClient.

The router is mounted on a small test app here, so these tests do not
depend on the shared backend/app/main.py.
"""

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.c3 import api, config

app = FastAPI()
app.include_router(api.router)
client = TestClient(app)

# FAO-56 Example 18 day (Brussels, 6 July = day 187 in 2024): ET0 3.88 mm/day.
EX18_DAY = {"date": "2024-07-05", "tmax_c": 21.5, "tmin_c": 12.3, "rh_mean_pct": 73.5,
            "rh_max_pct": 84.0, "rh_min_pct": 63.0, "rainfall_mm": 0.0,
            "wind_speed_2m_ms": 2.078, "solar_radiation_mj_m2_day": 22.07}
PLOT = {"latitude_deg": 7.9, "elevation_m": 150.0, "field_capacity_m3m3": 0.22,
        "wilting_point_m3m3": 0.10, "root_depth_m": 0.5, "depletion_fraction_p": 0.30,
        "area_m2": 50.0}


def test_status():
    response = client.get("/c3/status")
    assert response.status_code == 200
    assert "PROXY" in response.json()["crop_values"]


def test_et0_matches_fao56_example_18():
    response = client.post("/c3/et0", json={"latitude_deg": 50.80, "elevation_m": 100.0,
                                            "days": [EX18_DAY]})
    assert response.status_code == 200
    assert response.json()["et0_mm_day"][0] == pytest.approx(3.88, abs=0.05)


def test_et0_rejects_impossible_humidity():
    bad = dict(EX18_DAY, rh_mean_pct=150.0)
    response = client.post("/c3/et0", json={"latitude_deg": 0, "elevation_m": 0, "days": [bad]})
    assert response.status_code == 422


def test_plan_from_request_data():
    days = [dict(EX18_DAY, date=str(d.date()), tmax_c=32.0, tmin_c=23.0, rh_max_pct=None,
                 rh_min_pct=None, rh_mean_pct=75.0, solar_radiation_mj_m2_day=20.0)
            for d in pd.date_range("2025-06-02", periods=7)]
    body = {"soil_moisture_m3m3": 0.16, "forecast": days, "plot": PLOT, "kc": [1.05] * 7,
            "max_relative_et_deficit": 0.0}
    response = client.post("/c3/plan", json=body)
    assert response.status_code == 200
    result = response.json()
    assert result["today"]["date"] == "2025-06-02"
    assert result["today"]["irrigate"] is True
    assert len(result["plan"]) == 7


def test_plan_rejects_bad_plot_settings():
    days = [dict(EX18_DAY, date=str(d.date())) for d in pd.date_range("2025-06-02", periods=7)]
    body = {"soil_moisture_m3m3": 0.16, "forecast": days, "plot": {"latitude_deg": 7.9},
            "kc": [1.05] * 7, "max_relative_et_deficit": 0.0}
    assert client.post("/c3/plan", json=body).status_code == 422


def test_demo_plan_is_marked_synthetic():
    response = client.get("/c3/demo/plan", params={"issue_date": "2025-06-01",
                                                   "soil_moisture_m3m3": 0.16})
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == "synthetic" and "SYNTHETIC" in body["note"]
    assert body["today"]["irrigate"] is True


def test_demo_plan_unknown_date():
    assert client.get("/c3/demo/plan", params={"issue_date": "1999-01-01"}).status_code == 404


def test_demo_evaluation_missing_then_present(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    assert client.get("/c3/demo/evaluation").status_code == 404
    pd.DataFrame({"schedule": ["fixed"], "total_irrigation_mm": [1.23456]}).to_csv(
        tmp_path / "evaluation_synthetic.csv", index=False)
    body = client.get("/c3/demo/evaluation").json()
    assert body["data"] == "synthetic"
    assert body["rows"][0]["total_irrigation_mm"] == pytest.approx(1.235)


# --- live demo (no internet: the forecast download is replaced) --------------
def fake_live_forecast(monkeypatch, fail=False):
    def fetch(lat, lon, days=8):
        if fail:
            raise ConnectionError("offline")
        dates = pd.date_range("2026-10-21", periods=days)
        return pd.DataFrame({"date": dates, "tmax_c": 31.0, "tmin_c": 23.0, "rh_max_pct": 95.0,
                             "rh_min_pct": 65.0, "rh_mean_pct": 80.0,
                             "rainfall_mm": [0, 0, 12, 0, 0, 0, 0, 0],
                             "wind_speed_2m_ms": 2.0, "solar_radiation_mj_m2_day": 20.0})
    monkeypatch.setattr(api.weather_sources, "fetch_forecast", fetch)


def test_demo_live_plan(monkeypatch):
    fake_live_forecast(monkeypatch)
    response = client.get("/c3/demo/live-plan", params={"soil_moisture_m3m3": 0.16})
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == "live forecast" and "placeholders" in body["note"]
    assert body["location"]["name"].startswith("Mahailuppallama")
    assert body["today"]["date"] == "2026-10-21"
    assert len(body["days"]) == 7 and "12.0 mm rain forecast" in body["days"][2]["reason"]
    assert len(body["week_comparison"]) == 3


def test_demo_live_plan_when_forecast_service_is_down(monkeypatch):
    fake_live_forecast(monkeypatch, fail=True)
    assert client.get("/c3/demo/live-plan").status_code == 503


def test_demo_evaluation_real_missing_then_present(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    assert client.get("/c3/demo/evaluation-real").status_code == 404
    pd.DataFrame({"schedule": ["fixed"], "total_irrigation_mm": [10.0]}).to_csv(
        tmp_path / "evaluation_real_weather_demo_location.csv", index=False)
    body = client.get("/c3/demo/evaluation-real").json()
    assert body["data"] == "real weather and forecasts"
