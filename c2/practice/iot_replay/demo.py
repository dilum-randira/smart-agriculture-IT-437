"""Execute practice C1->C2 pipeline: simulated records -> hourly -> reference.

Does NOT access actual field hardware, does NOT train a model, and does NOT
demonstrate verified Nai Miris forecast accuracy.
"""
import argparse
import json
from datetime import timedelta

from forecast import forecast_from_hourly
from hourly import aggregate_complete_hours
from replay import generate_readings


def run_demo(hours=72, plot_id="practice_plot_01", mode="valid"):
    records = list(generate_readings(hours=hours, plot_id=plot_id))
    if mode == "missing":
        # Remove one quarter-hour record; the corresponding hour is excluded.
        del records[-9]
    elif mode != "valid":
        raise ValueError("mode must be valid or missing")
    hourly = aggregate_complete_hours(records)
    issued_at = records[-1]["recorded_at"] + timedelta(minutes=15)
    forecast = forecast_from_hourly(hourly, plot_id, issued_at,
                                    lookback_hours=48, horizon_hours=24)
    return {
        "note": "SYNTHETIC PRACTICE ONLY: persistence reference, not trained model",
        "received_records": len(records),
        "eligible_complete_hours": len(hourly),
        "prediction": forecast,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=int, default=72)
    parser.add_argument("--mode", choices=["valid", "missing"], default="valid")
    args = parser.parse_args()
    result = run_demo(hours=args.hours, mode=args.mode)
    print(json.dumps(result, indent=2))
