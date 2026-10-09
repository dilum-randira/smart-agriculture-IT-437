# C2 — Predictive Intelligence Framework

Individual research component of **J26-IT-437**: Explainable IoT Microclimate System for Smart Irrigation and Nai Miris Yield Forecasting.

## Scope

- **Microclimate:** forecast soil moisture, air temperature, and relative humidity at 24-hour, 3-day, and 7-day horizons. Primary candidate: Attention-based BiLSTM. Baselines: LSTM, GRU; simple reference: persistence.
- **Yield:** predict measured fresh Nai Miris yield (kg per plot in the following seven days). Primary candidate: XGBoost. Baselines: Random Forest and SVR; simple reference: training-set mean.
- Evaluate with leakage-aware temporal/plot splits, MAE/RMSE, yield R², and eventually prediction intervals and ablation tests.

**Data dependency:** C1 IoT hardware and measured harvest labels are not yet available. Any synthetic examples in `practice/` are for learning and code checks only, **not actual Nai Miris research evidence**. Public datasets must be audited for crop, unit, provenance, and target suitability before inclusion.

## First reproducible practice exercise

```bash
python -m pip install -r c2/requirements.txt
python c2/practice/yield_regression.py
python -m unittest discover -s c2/tests -v
```

This compares a training-set-mean reference against Random Forest using 300 **synthetic**, independently generated records. It reproduces the first Google Colab practice exercise. A random split is used **only for this educational synthetic example**, not for final field or time-series experiments.

## Roadmap

1. [In progress] Learn supervised regression and keep reproducible practice code.
2. [Next] Audit real public weather/yield datasets; define C1–C2 data contract.
3. [Next] Implement chronological forecasting pipeline and persistence baseline.
4. [Next] Train LSTM/GRU/Attention-BiLSTM on eligible data.
5. [Next] Develop Nai Miris yield models **when valid harvest labels exist**; otherwise publish a separate public-data feasibility experiment.
6. [Later] Prediction intervals, ablations, integration with C1/C3/C4, controlled monitoring.

Research results, figures, and model achievements are only reported after actual experiments. See `docs/experiment_log.md` for dated evidence.
