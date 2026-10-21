"""Tests for app/c3/stress_classifier.py (Stage 6 and Stage 8 part 2).

They check the pipeline works; scores on synthetic data are NOT accuracy claims.
"""

import pandas as pd
import pytest

from app.c3 import baselines as bl
from app.c3 import config
from app.c3 import data_loading as dl
from app.c3 import et0
from app.c3 import stress_classifier as sc

FC, ROOT = 0.22, 0.5
TAW, RAW = 60.0, 18.0


@pytest.fixture(scope="module")
def weather() -> pd.DataFrame:
    w = dl.load_weather(config.SAMPLE_DATA_DIR / "weather_synthetic_daily.csv")
    return et0.add_et0_column(w, 7.9, 150.0)


@pytest.fixture(scope="module")
def days(weather) -> pd.DataFrame:
    rule = bl.doa_schedule_rule(bl.doa_irrigation_days(len(weather), 5, 7, 1))
    return sc.build_training_days(weather, rule, [1.05] * len(weather), TAW, RAW, FC, ROOT)


def test_soil_moisture_from_depletion():
    assert sc.soil_moisture_from_depletion_m3m3(0.0, FC, ROOT) == pytest.approx(0.22)
    assert sc.soil_moisture_from_depletion_m3m3(25.0, FC, ROOT) == pytest.approx(0.17)


def test_stressed_tomorrow_without_irrigation():
    # 15 mm depleted + 5 mm use = 20 mm > RAW 18 -> stressed; with 10 mm rain -> 10 mm, not.
    assert sc.stressed_tomorrow_without_irrigation(15.0, 0.0, 5.0, TAW, RAW) is True
    assert sc.stressed_tomorrow_without_irrigation(15.0, 10.0, 5.0, TAW, RAW) is False


def test_build_training_days(days, weather):
    assert len(days) == len(weather)
    assert set(sc.FEATURES) | {"stressed_tomorrow", "date"} == set(days.columns)
    assert days["stressed_tomorrow"].nunique() == 2          # both classes present
    assert days["soil_moisture_m3m3"].iloc[0] == pytest.approx(FC)   # starts full


def test_train_predict_and_evaluate_on_held_out_year(days):
    train = days[days["date"].dt.year == 2024]
    test = days[days["date"].dt.year == 2025]
    model = sc.train_stress_classifier(train)
    probabilities = sc.predict_stress_probability(model, test)
    assert len(probabilities) == len(test)
    assert all(0.0 <= p <= 1.0 for p in probabilities)
    scores = sc.evaluate_classifier(model, test)
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        assert 0.0 <= scores[key] <= 1.0


def test_reactive_ml_rule_irrigates_dry_soil_not_full_soil(days, weather):
    model = sc.train_stress_classifier(days)
    rule = sc.reactive_ml_rule(model, weather, FC, ROOT)
    assert rule(100, 0.0) == 0.0               # full soil: no irrigation
    assert rule(100, 50.0) == pytest.approx(50.0)   # very dry soil: refill
