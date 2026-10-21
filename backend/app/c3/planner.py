"""Stage 10: today's irrigation recommendation (the adaptive schedule).

Called once per day (by the API) with the latest soil moisture reading and
the latest forecast, so the 7-day plan adapts as new data arrives. Joins
the pieces: soil moisture -> depletion (FAO-56 Eq. 87), forecast ->
scenarios and ET0, NSGA-II plan, risk and optional cost.
"""

import json
from dataclasses import dataclass

import pandas as pd

from app.c3 import baselines as bl
from app.c3 import cost
from app.c3 import optimiser as opt
from app.c3 import water_balance as wb


@dataclass
class PlotSettings:
    """Plot, soil and crop settings (units in the names). Values must come
    from the plot or a cited source; see config.py and the C3 README."""
    latitude_deg: float
    elevation_m: float
    field_capacity_m3m3: float
    wilting_point_m3m3: float
    root_depth_m: float
    depletion_fraction_p: float
    area_m2: float


def current_depletion_mm(soil_moisture_m3m3: float, plot: PlotSettings) -> float:
    """Root-zone depletion from a soil moisture reading, FAO-56 Eq. 87,
    kept inside 0..TAW (Eq. 86): wetter than field capacity counts as full."""
    taw = wb.total_available_water_mm(plot.field_capacity_m3m3, plot.wilting_point_m3m3,
                                      plot.root_depth_m)
    depletion = wb.depletion_from_soil_moisture_mm(plot.field_capacity_m3m3, soil_moisture_m3m3,
                                                   plot.root_depth_m)
    return min(max(depletion, 0.0), taw)


def plan_rule(irrigate: list[bool], refill_fraction: list[float] | None = None,
              min_irrigation_mm: float = 0.0) -> bl.IrrigationRule:
    """Turn a 7-day yes/no plan into an irrigation rule for the simulator."""
    def rule(day: int, depletion_mm: float) -> float:
        fraction = refill_fraction[day - 1] if refill_fraction else 1.0
        amount = fraction * depletion_mm
        return amount if irrigate[day - 1] and amount > 0 and amount >= min_irrigation_mm else 0.0
    return rule


def explain_days(rule: bl.IrrigationRule, start_depletion_mm: float,
                 scenario: opt.WeatherScenario, kc: list[float], taw_mm: float, raw_mm: float,
                 dates: list[str]) -> list[dict]:
    """Day-by-day facts behind a plan, if the forecast comes true: forecast
    rain and ET0, how dry the root zone is that morning, and the irrigation.
    The sentence only restates these numbers (no invented reasons)."""
    sim = bl.simulate_with_rule(rule, start_depletion_mm, scenario.et0_mm_day, kc,
                                scenario.rain_mm, taw_mm, raw_mm)
    before = [start_depletion_mm] + sim["depletion_end_mm"].tolist()[:-1]
    days = []
    for i, date in enumerate(dates):
        rain, dry, water = scenario.rain_mm[i], before[i], sim["irrigation_mm"].iloc[i]
        if water > 0:
            text = (f"Irrigate {water:.0f} mm: root zone {dry:.0f} mm dry "
                    f"(stress starts at {raw_mm:.0f} mm), {rain:.1f} mm rain forecast.")
        elif rain > 0:
            text = f"No irrigation: {rain:.1f} mm rain forecast; root zone {dry:.0f} mm dry."
        elif dry <= raw_mm:
            text = f"No irrigation: root zone {dry:.0f} mm dry, not yet at the {raw_mm:.0f} mm stress point."
        else:
            text = (f"No irrigation: root zone {dry:.0f} mm dry, past the {raw_mm:.0f} mm stress "
                    f"point; accepted within the allowed shortfall.")
        days.append({"date": date, "rain_forecast_mm": round(rain, 1),
                     "et0_mm_day": round(scenario.et0_mm_day[i], 2),
                     "depletion_morning_mm": round(dry, 1), "irrigation_mm": round(float(water), 1),
                     "reason": text})
    return days


def compare_week(rules: dict[str, bl.IrrigationRule], start_depletion_mm: float,
                 scenario: opt.WeatherScenario, kc: list[float], taw_mm: float,
                 raw_mm: float) -> list[dict]:
    """What each rule would do over the 7 days if the forecast comes true."""
    rows = []
    for name, rule in rules.items():
        sim = bl.simulate_with_rule(rule, start_depletion_mm, scenario.et0_mm_day, kc,
                                    scenario.rain_mm, taw_mm, raw_mm)
        etm = sum(k * e for k, e in zip(kc, scenario.et0_mm_day))
        rows.append({"schedule": name,
                     "water_mm": round(float(sim["irrigation_mm"].sum()), 1),
                     "irrigations": int((sim["irrigation_mm"] > 0).sum()),
                     "relative_et_deficit": round(opt.relative_et_deficit(sim["etc_adj_mm"].sum(), etm), 3),
                     "drainage_mm": round(float(sim["deep_percolation_mm"].sum()), 1)})
    return rows


def plan_today(soil_moisture_m3m3: float, forecasts: pd.DataFrame, issue_date: str,
               plot: PlotSettings, kc: list[float], max_relative_et_deficit: float,
               *, refill_fraction: list[float] | None = None, min_irrigation_mm: float = 0.0,
               water_price_lkr_per_m3: float | None = None, cost_per_event_lkr: float = 0.0,
               pop_size: int = opt.DEFAULT_POP_SIZE,
               n_generations: int = opt.DEFAULT_N_GENERATIONS) -> dict:
    """Today's recommendation plus the 7-day plan and the trade-off options.

    forecasts: C3 forecast format; lead day 1 of the issue on issue_date is
    TODAY (e.g. weather_sources.to_c3_forecasts with yesterday's date).
    kc and refill_fraction: one value per planned day (7).
    """
    taw = wb.total_available_water_mm(plot.field_capacity_m3m3, plot.wilting_point_m3m3,
                                      plot.root_depth_m)
    raw = wb.readily_available_water_mm(taw, plot.depletion_fraction_p)
    depletion = current_depletion_mm(soil_moisture_m3m3, plot)
    scenarios = opt.forecast_scenarios(forecasts, issue_date, plot.latitude_deg, plot.elevation_m)
    front = opt.optimise_schedule(depletion, scenarios, kc, taw, raw, min_irrigation_mm,
                                  pop_size, n_generations, refill_fraction=refill_fraction)
    if water_price_lkr_per_m3 is not None:
        front = cost.add_cost_column(front, plot.area_m2, water_price_lkr_per_m3, cost_per_event_lkr)
    try:
        chosen = opt.least_water_schedule(front, max_relative_et_deficit)
        meets_allowed_deficit = True
    except ValueError:
        chosen = front.sort_values("relative_et_deficit").iloc[0]
        meets_allowed_deficit = False

    today_fraction = refill_fraction[0] if refill_fraction else 1.0
    amount_mm = today_fraction * depletion if bool(chosen["day1_irrigate"]) else 0.0
    if amount_mm < min_irrigation_mm:
        amount_mm = 0.0
    target_dates = forecasts[forecasts["issue_date"] == pd.Timestamp(issue_date)] \
        .sort_values("lead_day")["target_date"].dt.strftime("%Y-%m-%d").tolist()

    # Explanation and "predictive vs reactive" for this week, if the forecast comes true.
    flags = [bool(chosen[f"day{i + 1}_irrigate"]) for i in range(len(kc))]
    c3_rule = plan_rule(flags, refill_fraction, min_irrigation_mm)
    blind_front = opt.optimise_schedule(depletion, [scenarios[1]], kc, taw, raw, min_irrigation_mm,
                                        pop_size, n_generations, refill_fraction=refill_fraction)
    try:
        blind = opt.least_water_schedule(blind_front, max_relative_et_deficit)
    except ValueError:
        blind = blind_front.sort_values("relative_et_deficit").iloc[0]
    blind_flags = [bool(blind[f"day{i + 1}_irrigate"]) for i in range(len(kc))]
    week_rules = {
        "C3 (uses the forecast)": c3_rule,
        "C3 ignoring forecast rain": plan_rule(blind_flags, refill_fraction, min_irrigation_mm),
        "Fixed threshold (reacts to soil only)": bl.fixed_threshold_rule(raw),
    }
    days = explain_days(c3_rule, depletion, scenarios[0], kc, taw, raw, target_dates)

    return {
        "today": {
            "date": target_dates[0],
            "irrigate": amount_mm > 0,
            "amount_mm": round(amount_mm, 2),
            "volume_m3": round(cost.water_volume_m3(amount_mm, plot.area_m2), 3),
        },
        "soil": {"depletion_mm": round(depletion, 2), "taw_mm": round(taw, 2),
                 "raw_mm": round(raw, 2)},
        # What would actually be applied each day if the forecast comes true
        # (a planned irrigation on an already-full root zone applies 0 mm).
        "plan": [{"date": day["date"], "irrigate": day["irrigation_mm"] > 0,
                  "amount_mm": day["irrigation_mm"]} for day in days],
        "days": days,
        "week_comparison": compare_week(week_rules, depletion, scenarios[0], kc, taw, raw),
        "chosen_objectives": {k: float(chosen[k]) for k in opt.OBJECTIVES},
        "meets_allowed_deficit": meets_allowed_deficit,
        # to_json -> json.loads gives plain Python types (no numpy) for the API
        "pareto_front": json.loads(front.to_json(orient="records")),
    }
