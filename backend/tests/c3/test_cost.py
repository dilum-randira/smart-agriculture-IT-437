"""Tests for app/c3/cost.py. Prices here are test numbers, not real prices."""

import pandas as pd
import pytest

from app.c3 import cost


def test_water_volume_m3():
    # 10 mm over 50 m2 = 500 litres = 0.5 m3.
    assert cost.water_volume_m3(10.0, 50.0) == pytest.approx(0.5)


def test_irrigation_cost_with_and_without_event_cost():
    assert cost.irrigation_cost_lkr(10.0, 2, 50.0, water_price_lkr_per_m3=100.0) == pytest.approx(50.0)
    assert cost.irrigation_cost_lkr(10.0, 2, 50.0, 100.0, cost_per_event_lkr=20.0) == pytest.approx(90.0)


def test_add_cost_column_keeps_input_unchanged():
    table = pd.DataFrame({"total_water_mm": [0.0, 20.0], "irrigation_events": [0, 1]})
    out = cost.add_cost_column(table, area_m2=50.0, water_price_lkr_per_m3=100.0)
    assert out["cost_lkr"].tolist() == pytest.approx([0.0, 100.0])
    assert "cost_lkr" not in table.columns


def test_add_cost_column_with_other_column_names():
    table = pd.DataFrame({"total_irrigation_mm": [20.0], "irrigation_events": [2]})
    out = cost.add_cost_column(table, 50.0, 100.0, cost_per_event_lkr=5.0,
                               water_col="total_irrigation_mm")
    assert out["cost_lkr"].iloc[0] == pytest.approx(110.0)
