"""Stage 6: water stress probability classifier (Random Forest).

Question it answers each morning: "If we do not irrigate today, will the
crop be water-stressed tomorrow?"

LABEL (interim, agreed with the student; to be confirmed with the
supervisor): stressed = FAO-56 Ks < 1 tomorrow, i.e. tomorrow's starting
depletion > RAW (FAO-56 Eq. 84) if no water is added today.
CAVEAT: on simulated data the labels come from the same water balance the
features describe, so the model partly re-learns FAO-56. Scores on
synthetic data test the pipeline only; they are NOT model accuracy.
Real labels (e.g. observed wilting, leaf water potential) would fix this.

Features use only what is observable in the morning: soil moisture (C1
sensor) and today's weather / ET0 (forecast).
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from app.c3 import baselines as bl
from app.c3 import water_balance as wb

FEATURES = ["soil_moisture_m3m3", "et0_mm_day", "tmax_c", "rh_mean_pct", "rainfall_mm"]


def soil_moisture_from_depletion_m3m3(depletion_mm: float, field_capacity_m3m3: float,
                                      root_depth_m: float) -> float:
    """Volumetric soil moisture (m3/m3) from depletion. FAO-56 Eq. 87 rearranged."""
    return field_capacity_m3m3 - depletion_mm / (1000.0 * root_depth_m)


def stressed_tomorrow_without_irrigation(depletion_mm: float, rain_mm: float, etc_mm: float,
                                         taw_mm: float, raw_mm: float) -> bool:
    """Label: tomorrow's starting depletion > RAW if no irrigation today (Ks < 1, Eq. 84)."""
    tomorrow, _ = wb.daily_depletion_mm(depletion_mm, rain_mm, 0.0, etc_mm, taw_mm)
    return tomorrow > raw_mm


def build_training_days(weather: pd.DataFrame, rule: bl.IrrigationRule, kc: list[float],
                        taw_mm: float, raw_mm: float, field_capacity_m3m3: float,
                        root_depth_m: float) -> pd.DataFrame:
    """Simulate `rule` over the weather table (needs et0_mm_day) and return one
    row per day: FEATURES, the label 'stressed_tomorrow' and the date."""
    sim = bl.simulate_with_rule(rule, 0.0, weather["et0_mm_day"].tolist(), kc,
                                weather["rainfall_mm"].tolist(), taw_mm, raw_mm)
    # Depletion at the START of each day = end of the previous day (0 on day 1).
    start_depletion = [0.0] + sim["depletion_end_mm"].tolist()[:-1]
    rows = []
    for i, depletion in enumerate(start_depletion):
        day = weather.iloc[i]
        ks = wb.water_stress_coefficient(depletion, taw_mm, raw_mm)
        etc = ks * wb.crop_et_mm_day(kc[i], day["et0_mm_day"])
        rows.append({
            "date": day["date"],
            "soil_moisture_m3m3": soil_moisture_from_depletion_m3m3(depletion, field_capacity_m3m3,
                                                                    root_depth_m),
            "et0_mm_day": day["et0_mm_day"],
            "tmax_c": day["tmax_c"],
            "rh_mean_pct": day["rh_mean_pct"],
            "rainfall_mm": day["rainfall_mm"],
            "stressed_tomorrow": stressed_tomorrow_without_irrigation(
                depletion, day["rainfall_mm"], etc, taw_mm, raw_mm),
        })
    return pd.DataFrame(rows)


def train_stress_classifier(days: pd.DataFrame, seed: int = 1) -> RandomForestClassifier:
    """Fit a Random Forest on FEATURES -> stressed_tomorrow.

    scikit-learn default settings (100 trees); seed only makes it repeatable.
    """
    model = RandomForestClassifier(random_state=seed)
    model.fit(days[FEATURES], days["stressed_tomorrow"])
    return model


def predict_stress_probability(model: RandomForestClassifier, features: pd.DataFrame) -> list[float]:
    """Probability (0-1) that the crop will be stressed tomorrow without irrigation."""
    stressed_column = list(model.classes_).index(True)
    return model.predict_proba(features[FEATURES])[:, stressed_column].tolist()


def evaluate_classifier(model: RandomForestClassifier, days: pd.DataFrame) -> dict:
    """Standard scikit-learn scores on held-out days (SYNTHETIC: pipeline check only)."""
    truth = days["stressed_tomorrow"]
    predicted = model.predict(days[FEATURES])
    scores = {
        "n_days": len(days),
        "stressed_share": float(truth.mean()),
        "accuracy": accuracy_score(truth, predicted),
        "precision": precision_score(truth, predicted, zero_division=0),
        "recall": recall_score(truth, predicted, zero_division=0),
        "f1": f1_score(truth, predicted, zero_division=0),
    }
    if truth.nunique() == 2:   # ROC AUC needs both classes
        scores["roc_auc"] = roc_auc_score(truth, predict_stress_probability(model, days))
    return scores


def reactive_ml_rule(model: RandomForestClassifier, weather: pd.DataFrame,
                     field_capacity_m3m3: float, root_depth_m: float,
                     probability_threshold: float = 0.5) -> bl.IrrigationRule:
    """Stage 8 part 2: reactive ML baseline.

    Each morning: predict stress for tomorrow from today's soil moisture and
    weather; if the probability >= probability_threshold, refill to field
    capacity. 0.5 is the standard classification cut-off (the same as
    model.predict), not an agronomic value. Generic method: align it with
    the "Paper 8" methodology once that paper is identified.
    """
    def rule(day: int, depletion_mm: float) -> float:
        today = weather.iloc[[day - 1]].copy()
        today["soil_moisture_m3m3"] = soil_moisture_from_depletion_m3m3(
            depletion_mm, field_capacity_m3m3, root_depth_m)
        probability = predict_stress_probability(model, today)[0]
        return depletion_mm if probability >= probability_threshold else 0.0
    return rule
