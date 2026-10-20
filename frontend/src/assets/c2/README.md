# C2 public presentation assets

`nai-miris-plant.svg` is an original vector illustration created for this frontend.
It uses no third-party artwork or external URLs, and is covered by the repository's
license. It is decorative botanical artwork, not a scientific plant simulation.

The two CSVs are exact, public-facing aggregate snapshots of:

- `backend/experiments/c2/yield/yield_final_test_metrics.csv`
- `backend/experiments/c2/yield/shap_feature_importance.csv`

Only these aggregate outputs are bundled. No datasets, individual predictions,
model artifacts, or metadata containing private information are included.
To refresh the display after a reviewed experiment, copy these two source files
into this directory and rebuild. The frontend formats the source values to three
decimals. The source SHAP value for flowering is `36.62012`.
