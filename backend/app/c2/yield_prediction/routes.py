
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel, Field

from .training import FEATURES


router = APIRouter(
    prefix="/api/c2/yield",
    tags=["C2 Yield Prediction"],
)

BACKEND = Path(__file__).resolve().parents[3]

MODEL_FILE = (
    BACKEND / "models/c2/yield"
    / "xgboost_tuned_development.joblib"
)


class YieldPredictionInput(BaseModel):
    plant_height_cm: float = Field(ge=0)
    main_branches: float = Field(ge=0)
    leaf_length_cm: float = Field(ge=0)
    leaf_breadth_cm: float = Field(ge=0)
    days_to_50pct_flowering: float = Field(gt=0)


@lru_cache(maxsize=1)
def load_model():
    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_FILE}"
        )

    # Only load model files produced and trusted locally.
    return joblib.load(MODEL_FILE)


@router.post("/predict")
def predict_yield(data: YieldPredictionInput):
    model = load_model()

    input_df = pd.DataFrame(
        [data.model_dump()],
        columns=FEATURES,
    )

    prediction = float(model.predict(input_df)[0])

    return {
        "predicted_yield_g_per_plant": round(
            prediction, 2
        ),
        "model": "Tuned XGBoost",
        "prediction_type": "experimental_trait_based_yield_estimate",
        "yield_weight_basis": "not_verified_fresh_or_dry",
        "unit": "g/plant",
        "warning": (
            "Research prototype trained on published "
            "genotype-year aggregates. Not validated "
            "for Sri Lankan field-level fresh yield."
        ),
    }
