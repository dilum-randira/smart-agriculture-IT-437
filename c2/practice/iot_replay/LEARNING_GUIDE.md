# Practice 03 — IoT → C2 Pipeline: Reliability Extension

**Scope:** This is an educational *synthetic replay* only. No C1 device connection, calibrated soil water measurement, measured Nai Miris yield labels, trained neural network forecast, or field-validation claim exists in this exercise.

## Today’s concepts / සිංහලෙන්

1. **Issue-time safety (`forecast.py`)** — Forecast timestamps must be later than the time the prediction was issued. Latest sensor history may be a little old; this must not produce an already-expired forecast step.
2. **Sensor audit (`audit.py`)** — Required fields, timestamps and physical ranges validate කරනවා. Duplicate records නැවත ගණන් කරන්නේ නැහැ. Conflicting timestamps quarantine කරනවා.
3. **Growth-stage as-of (`stages.py`)** — Observation එක පසුව system එකට ඇතුළු කරලා තිබුණොත්, ඒ stage එක කලින් issue කළ prediction එකට දාන්න බැහැ. මේක *data leakage* වැළැක්වීමට වැදගත්.
4. **C2 output contract (`contracts.py`)** — `prediction_id`, `plot_id`, `issued_at`, `target_start`, `target_end`, `variable`, `unit`, `model_version`, `data_version`, `status` වගේ fields versioned output එකකට දානවා. No uncertainty interval has been estimated; `lower`, `upper` and `interval_level` stay `null`.
5. **Test scenarios (`scenarios.py`)** — Good data gives `provisional`; missing/conflicting history gives `unavailable`; old inputs give `stale`.

## Run in Google Colab

After cloning (or pulling) branch `feature/c2-ml-foundation`:

```python
%cd /content/smart-agriculture-IT-437
!git switch feature/c2-ml-foundation
!git pull --ff-only
!python -m unittest discover -s c2/tests -v
!python c2/practice/iot_replay/scenarios.py
```

An existing Colab runtime might need `!pip -q install -r c2/requirements.txt matplotlib` for the complete test suite.

## Important notes for PP1

- These files show **input-contract and failure-handling practice**, not completed C2 model development.
- Real C1 data needs sensor metadata, validated measurement units, timestamps, quality flags and stage/harvest records supplied through an agreed interface.
- The output is an **untrained persistence reference**, not Attention-BiLSTM or XGBoost.
- Fresh-yield validation requires measured plot-linked harvest targets. Synthetic crop yields cannot validate a Nai Miris yield model.
- This branch is intentionally separate from the actual component feature branch and the stable `main` branch.
