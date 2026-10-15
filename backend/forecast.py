from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def build_price_forecast(farm):
    """Hold the mean of the latest three observations fixed for seven days."""
    as_of = date.fromisoformat(farm["as_of_date"])
    observations = {}
    for row in farm["market"]["price_history"]:
        observed_on = date.fromisoformat(row["date"])
        if observed_on > as_of:
            continue
        if observed_on in observations:
            raise ValueError("Price history contains duplicate dates.")
        try:
            price = Decimal(str(row["price_lkr_per_kg"]))
        except InvalidOperation as exc:
            raise ValueError("Prices must be finite, non-negative numbers.") from exc
        if not price.is_finite() or price < 0:
            raise ValueError("Prices must be finite, non-negative numbers.")
        observations[observed_on] = price
    if len(observations) < 3:
        raise ValueError("At least three price observations on or before the farm date are required.")
    selected_dates = sorted(observations)[-3:]
    mean = sum(observations[day] for day in selected_dates) / Decimal(3)
    predicted_price = float(mean.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return {
        "farm_id": farm["farm_id"],
        "as_of_date": as_of.isoformat(),
        "method": "last_three_observations_mean",
        "currency": "LKR",
        "price_unit": "LKR/kg",
        "horizon_days": 7,
        "latest_price_date": selected_dates[-1].isoformat(),
        "latest_price_age_days": (as_of - selected_dates[-1]).days,
        "input_observations": [
            {"date": day.isoformat(), "price_lkr_per_kg": float(observations[day])}
            for day in selected_dates
        ],
        "explanation": "Average the last three recorded prices on or before the farm date and hold that value constant for the next seven days. Forecasts are not fed back into the average.",
        "limitations": "Baseline with retrospective evaluation, not validated future accuracy. No trend, weather, seasonality or uncertainty interval is modeled. Dates follow the selected decision date. The three latest observations may not be consecutive days; missing dates are not filled. See provenance for the data source.",
        "forecast": [
            {
                "date": (as_of + timedelta(days=offset)).isoformat(),
                "predicted_price_lkr_per_kg": predicted_price,
            }
            for offset in range(1, 8)
        ],
    }
