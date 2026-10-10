"""Google Colab-friendly first LSTM practice; synthetic temperature ONLY.

Run AFTER installing TensorFlow. Prints actual results after training completes.
No benchmark result is claimed before you run it. Not Nai Miris validation.
"""

from synthetic_weather import make_synthetic_hourly_weather
from windows import chronological_windows
from persistence import horizon_scores, persistence_forecast
from scaling import fit_train_only_scaler, transform_splits, inverse_forecast


def main():
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit("TensorFlow unavailable. Open Google Colab and run this script there.") from exc

    tf.keras.utils.set_random_seed(42)
    weather = make_synthetic_hourly_weather()
    temperature = weather["air_temperature_c"].to_numpy()
    lookback, horizon = 48, 24  # small PRACTICE, not final C2's 336/168
    raw = chronological_windows(temperature, lookback, horizon, stride=6)
    scaler = fit_train_only_scaler(raw)
    scaled = transform_splits(raw, scaler)

    train, valid, test = (scaled[k] for k in ("train", "validation", "test"))
    print("SYNTHETIC PRACTICE ONLY — not real farm sensor data")
    print("Training / validation / test windows:", *(len(scaled[k]["X"]) for k in ("train", "validation", "test")))

    model = tf.keras.Sequential([
        tf.keras.Input(shape=(lookback, 1)),
        tf.keras.layers.LSTM(32),
        tf.keras.layers.Dense(horizon),
    ])
    model.compile(optimizer="adam", loss="mse")
    model.fit(
        train["X"], train["y"],
        validation_data=(valid["X"], valid["y"]),
        epochs=20, batch_size=32,
        callbacks=[tf.keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True)],
        verbose=2,
    )
    predicted = inverse_forecast(model.predict(test["X"], verbose=0), scaler)
    baseline = persistence_forecast(raw["test"]["X"], horizon)
    actual = raw["test"]["y"]
    print("\nTest errors in degrees Celsius (only after training):")
    for label, forecast in (("Persistence", baseline), ("LSTM", predicted)):
        print(label, horizon_scores(actual, forecast, horizons=(6, 12, 24)))
    print("Note: correlated rolling windows are not independent field replications.")


if __name__ == "__main__":
    main()
