"""Irrigation cost (LKR) from water used and number of irrigation events.

cost = water volume x water price + events x cost per event

NSGA-II already minimises water and events as separate objectives, so every
cost trade-off is already on the Pareto front. Cost is therefore calculated
for reporting and for choosing a plan, not added as another objective.

Prices are NOT set here: the water price (LKR/m3) and any cost per event
(pumping, labour) must come from the farmer or the Irrigation Department.
"""

import pandas as pd

LITRES_PER_M3 = 1000.0   # definition


def water_volume_m3(water_mm: float, area_m2: float) -> float:
    """Water depth (mm) over an area (m2) -> volume (m3).

    1 mm of water over 1 m2 is 1 litre (definition of mm depth).
    """
    return water_mm * area_m2 / LITRES_PER_M3


def irrigation_cost_lkr(water_mm: float, events: int, area_m2: float,
                        water_price_lkr_per_m3: float, cost_per_event_lkr: float = 0.0) -> float:
    """Total irrigation cost in LKR for a plan or a season."""
    return water_volume_m3(water_mm, area_m2) * water_price_lkr_per_m3 + events * cost_per_event_lkr


def add_cost_column(table: pd.DataFrame, area_m2: float, water_price_lkr_per_m3: float,
                    cost_per_event_lkr: float = 0.0, water_col: str = "total_water_mm",
                    events_col: str = "irrigation_events") -> pd.DataFrame:
    """Copy of a plans / schedules table with an extra 'cost_lkr' column."""
    out = table.copy()
    out["cost_lkr"] = [irrigation_cost_lkr(w, e, area_m2, water_price_lkr_per_m3, cost_per_event_lkr)
                       for w, e in zip(out[water_col], out[events_col])]
    return out
