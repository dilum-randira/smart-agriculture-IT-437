# smart-agriculture-IT-437

### Explainable IoT Microclimate System for Smart Irrigation and Nai Miris Yield Forecasting

An AI and IoT-based smart agriculture research project focused on smart irrigation, microclimate forecasting, yield prediction, and farmer decision support.

## 👥 Team Members

- Bandara W.V.L
- Kumara H.P.D.D.R.H
- Gayantha W.M.K
- Kumari U.S.S.S

## 📌 IT4010 Research Project
**SLIIT | 2026**

---

## C4 — Explainable Decision Support, Market Intelligence & Harvest Optimization

**Component branch:** `feature/c4`
**Documentation updated:** 12 October 2026

### Purpose

C4 helps compare possible Nai Miris harvest dates using market prices, harvestable yield, costs and irrigation requirements. The intended completed system will apply feasibility constraints and farmer preferences, then explain its recommended option.

### Implemented in the local prototype

- **Backend:** FastAPI endpoints for farm data, source inspection, price forecasts and harvest comparisons.
- **Dashboard:** HTML, CSS and JavaScript interface for source selection, editable harvestable yield, forecasts, cost breakdowns and evaluation results.
- **Market baseline:** mean of the last three recorded prices, held constant over the next seven days.
- **Harvest scenarios:** compare harvesting on the scenario date, three days later and seven days later.
- **Economic calculations:** revenue minus selected harvesting, transport and additional irrigation costs. These returns are not full farm profit.
- **Feasibility checks:** earliest harvest-ready date, latest acceptable date and total available additional irrigation water. Excluded options show reasons; no option is selected when all fail.
- **Yield inputs:** enter kilograms directly or scale a selected Kaggle Harvesting-stage record using an explicitly supplied plant count.
- **Research evaluation:** chronological baseline comparisons and trained Random Forest candidates for +1, +3 and +7 days.

The highest-return highlight considers eligible options only. Farmer-preference scoring and risk-aware recommendations are not implemented yet.

### Data sources

| Source | Saved coverage | Use and limitations |
| --- | --- | --- |
| [Dambulla Nai Miris prices](https://api.dambulladec.com/api/prices/product/68/chart) | 475 observations, 5 May 2025–5 October 2026 | Original minimum/maximum prices retained; arithmetic midpoint used for forecasting. There are 44 missing calendar dates, which are not filled. Midpoint is not a guaranteed farm-gate selling price. |
| [Sri Lankan Nai Miris Agronomic Dataset](https://www.kaggle.com/datasets/isurujayasuriya452/sri-lankan-nai-miris-agronomic-dataset) | 15,000 records, 31 columns, 1 January 2025–28 February 2026 | Historical agronomic reference. Yield is grams per plant; field collection and measured-versus-generated origin are unverified. This dataset has no market-price column. |
| Synthetic farm fixture | One demonstration farm | Mock component inputs, illustrative irrigation and costs. These are not observed farm measurements. |
| Farmer-preference survey | Questions reviewed; responses not imported | Intended to inform priorities, risk preferences and explanation requirements. Not a price-model training dataset. |

The external snapshots were retrieved on **6 October 2026** and are not refreshed automatically. The prototype's fixed scenario date is also **6 October 2026**; “today” refers to that scenario date rather than the actual current date. Entered yield is an estimate supplied by the user, not a sensor measurement.


### Technology and local structure

- Python 3.13, FastAPI and Uvicorn.
- NumPy and pandas for data work; scikit-learn for Random Forest experiments.
- Matplotlib for research charts.
- HTML, CSS and JavaScript for the dashboard, served by FastAPI.
- Python unittest and optional Playwright/Microsoft Edge browser checks.

The existing local implementation is organized as follows; these folders are **not yet included in this branch**:

```text
backend/          API, calculations, source adapters, training and tests
frontend/         Dashboard page, styles and interaction code
data/             Source snapshots, prepared data and synthetic fixture
models/price-v1/  Trained candidates and experiment metadata
docs/             Guides, survey mapping and evaluation reports
```

