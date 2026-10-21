"""Tests for app/c3/scripts/tune_nsga2.py (small grid so it runs quickly)."""

import pandas as pd

from app.c3 import optimiser as opt
from app.c3.scripts import tune_nsga2 as tune


def test_front_recovery_counts_found_objective_vectors():
    exact = pd.DataFrame({"total_water_mm": [0.0, 10.0], "relative_et_deficit": [0.5, 0.0],
                          "irrigation_events": [0.0, 1.0], "root_rot_risk_days": [0.0, 0.0]})
    assert tune.front_recovery(exact, exact) == 1.0
    assert tune.front_recovery(exact.iloc[[0]], exact) == 0.5


def test_test_cases_cover_days_and_soil_states():
    from app.c3 import config, data_loading as dl
    forecasts = dl.load_forecasts(config.SAMPLE_DATA_DIR / "c2_forecast_synthetic_7day.csv")
    cases = tune.test_cases("2025-05-01", 60.0, 18.0, 7.9, 150.0, forecasts)
    assert len(cases) == tune.CASE_DAYS * 4          # 4 soil states per forecast day
    assert {d for _, d in cases} == {0.0, 9.0, 18.0, 39.0}


def test_main_small_grid():
    table = tune.main(pop_sizes=[10], generations=[5], max_cases=2)
    assert list(table.columns) == ["pop_size", "n_generations", "evaluations",
                                   "mean_recovery", "worst_recovery"]
    assert table["mean_recovery"].between(0, 1).all()


def test_defaults_are_inside_the_tuning_grid():
    assert opt.DEFAULT_POP_SIZE in tune.POP_SIZES
    assert opt.DEFAULT_N_GENERATIONS in tune.GENERATIONS
