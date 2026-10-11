"""Educational LSTM vs GRU comparison on SYNTHETIC hourly temperatures.

Run in Colab after installing TensorFlow; importing this module does NOT train.
Results cannot validate real Nai Miris field accuracy.
"""
import argparse
from pathlib import Path
import numpy as np

from diagnostics import cumulative_metrics
from persistence import persistence_forecast
from scaling import fit_train_only_scaler, inverse_forecast, transform_splits
from seasonal_naive import seasonal_naive_forecast
from synthetic_weather import make_synthetic_hourly_weather
from windows import chronological_windows

LOOKBACK, HORIZON = 48, 24


def prepare_practice_windows():
    series = make_synthetic_hourly_weather()["air_temperature_c"].to_numpy()
    original = chronological_windows(series, lookback=LOOKBACK, horizon=HORIZON, stride=6)
    scaler = fit_train_only_scaler(original)
    return original, transform_splits(original, scaler), scaler


def make_recurrent_model(tf, architecture):
    if architecture not in ("LSTM", "GRU"):
        raise ValueError("architecture must be LSTM or GRU")
    layer = tf.keras.layers.LSTM if architecture == "LSTM" else tf.keras.layers.GRU
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(LOOKBACK, 1)),
        layer(32),
        tf.keras.layers.Dense(HORIZON),
    ])
    model.compile(optimizer="adam", loss="mse")
    return model


def train_and_compare(output_path, epochs=20, batch_size=32):
    if epochs < 1 or batch_size < 1:
        raise ValueError("epochs and batch_size must be positive")
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit("TensorFlow missing: use Google Colab or install TensorFlow.") from exc

    original, scaled, scaler = prepare_practice_windows()
    actual = original["test"]["y"]
    forecasts = {
        "persistence": persistence_forecast(original["test"]["X"], HORIZON),
        "seasonal": seasonal_naive_forecast(original["test"]["X"], HORIZON, 24),
    }

    for architecture in ("LSTM", "GRU"):
        tf.keras.backend.clear_session()
        tf.keras.utils.set_random_seed(42)
        model = make_recurrent_model(tf, architecture)
        model.fit(
            scaled["train"]["X"], scaled["train"]["y"],
            validation_data=(scaled["validation"]["X"], scaled["validation"]["y"]),
            epochs=epochs, batch_size=batch_size, verbose=2,
            callbacks=[tf.keras.callbacks.EarlyStopping(
                patience=3, restore_best_weights=True)],
        )
        predicted = model.predict(scaled["test"]["X"], verbose=0)
        forecasts[architecture.lower()] = inverse_forecast(predicted, scaler)

    print("SYNTHETIC PRACTICE ONLY — errors in °C; not real field accuracy")
    for name, predicted in forecasts.items():
        print(name, cumulative_metrics(actual, predicted, horizons=(6, 12, 24)))
    print("Overlapping window errors are not independent field replications.")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path, actual=actual, test_origins=original["test"]["origins"],
        synthetic_marker=np.array("SYNTHETIC_PRACTICE_ONLY"),
        variable=np.array("air_temperature_c"), **forecasts,
    )
    print("Saved synthetic practice predictions:", path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output", default="c2/artifacts/practice02_comparison.npz")
    args = parser.parse_args()
    train_and_compare(args.output, epochs=args.epochs, batch_size=args.batch_size)
