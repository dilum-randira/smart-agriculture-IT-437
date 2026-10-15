from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from forecast import build_price_forecast


def nonnegative(value):
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Yield, prices and costs must be finite non-negative numbers.") from exc
    if not number.is_finite() or number < 0:
        raise ValueError("Yield, prices and costs must be finite non-negative numbers.")
    return number


def money(value):
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def compare_harvests(farm):
    forecast = build_price_forecast(farm)
    as_of = date.fromisoformat(farm["as_of_date"])
    if farm["currency"] != "LKR":
        raise ValueError("This demo supports LKR only.")
    inputs = farm["mock_component_outputs"]
    yield_kg = nonnegative(inputs["c2"]["harvestable_yield_kg"])
    water_per_day = nonnegative(inputs["c3"]["irrigation_requirement_liters_per_day"])
    costs = farm["costs"]
    harvest_rate = nonnegative(costs["harvesting_lkr_per_kg"])
    transport = nonnegative(costs["transport_lkr_per_trip"])
    water_rate = nonnegative(costs["irrigation_lkr_per_liter"])
    latest = forecast["input_observations"][-1]
    scenarios = []
    for days in (0, 3, 7):
        price = nonnegative(latest["price_lkr_per_kg"] if days == 0 else forecast["forecast"][days - 1]["predicted_price_lkr_per_kg"])
        water = water_per_day * days
        revenue = Decimal(str(money(yield_kg * price)))
        harvesting = Decimal(str(money(yield_kg * harvest_rate)))
        irrigation = Decimal(str(money(water * water_rate)))
        transport_cost = Decimal(str(money(transport)))
        total = harvesting + irrigation + transport_cost
        scenarios.append({
            "days_until_harvest": days,
            "harvest_date": (as_of + timedelta(days=days)).isoformat(),
            "harvestable_yield_kg": float(yield_kg),
            "price_lkr_per_kg": float(price),
            "price_source": ("latest_" + farm["market"]["source"] + "_observation") if days == 0 else forecast["method"],
            "price_reference_date": latest["date"] if days == 0 else (as_of + timedelta(days=days)).isoformat(),
            "additional_irrigation_liters": float(water),
            "revenue_lkr": money(revenue),
            "costs_lkr": {"harvesting": money(harvesting), "transport": money(transport_cost), "additional_irrigation": money(irrigation)},
            "total_selected_costs_lkr": money(total),
            "net_return_after_selected_costs_lkr": money(revenue - total),
        })
    return {
        "farm_id": farm["farm_id"], "as_of_date": as_of.isoformat(), "currency": "LKR",
        "latest_price_date": forecast["latest_price_date"],
        "latest_price_age_days": forecast["latest_price_age_days"],
        "assumptions": [
            "Today means the selected decision date, which may differ from the computer date.",
            "Harvestable yield is held constant; all harvested produce is assumed sold.",
            "Today uses the latest observed price on or before the farm date, which may be older; delayed harvests use the baseline forecast. See provenance for source and price basis.",
            "One transport trip is charged for each alternative. Alternatives are mutually exclusive.",
            "Additional irrigation equals daily requirement multiplied by days of delay; today has zero additional waiting cost.",
            "Money is rounded to two decimals per line item before totals are calculated.",
        ],
        "formulas": {
            "revenue": "yield_kg * price_lkr_per_kg",
            "harvesting_cost": "yield_kg * harvesting_lkr_per_kg",
            "additional_irrigation_cost": "days_until_harvest * liters_per_day * irrigation_lkr_per_liter",
            "net_return": "revenue - harvesting_cost - transport_cost - additional_irrigation_cost",
        },
        "limitations": "Illustrative returns after selected incremental costs, not full farm profit. Yield growth, losses and weather risks are not modeled. Optional preference ranking is reported separately. Optional feasibility checks cover supplied dates and additional irrigation only. The economic comparison alone is not a personalized recommendation.",
        "scenarios": scenarios,
    }
