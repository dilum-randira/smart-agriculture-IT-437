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

### Repository status

This update adds **C4 documentation only**. The implementation described below has been developed and tested in a separate local workspace; its source code, datasets and model artifacts have not yet been committed to this branch. The startup commands below apply to that existing local workspace and will not run from a fresh clone of this documentation-only branch.

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

### Model experiment

One fixed Random Forest configuration was evaluated against last-price and three-observation-average baselines. Features use price observations at or before the forecast origin, rolling summaries, price changes, observation gaps and calendar information.

- Training outcomes: through **4 May 2026**.
- Validation outcomes: through **19 July 2026**.
- Final chronological period: through **5 October 2026**.
- Missing target dates are skipped; scoring pairs crossing split boundaries are excluded.

Final-period mean absolute error (**LKR/kg; lower is better**):

| Horizon | Three-observation average | Random Forest |
| --- | ---: | ---: |
| +1 day | 94.13 | 115.16 |
| +3 days | 97.38 | 115.46 |
| +7 days | 107.93 | 114.71 |

Random Forest improved one-day validation MAE, but that improvement did not persist in the final period. The dashboard therefore retains the average baseline. Model artifacts and research reports are saved locally.

This is retrospective snapshot evaluation, not a fully untouched or real-time historical test: overall baseline results had already been inspected, and source publication delays/revisions are not modeled. Results do not guarantee future accuracy.

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

### Run the existing local implementation

From PowerShell on the development computer:

```powershell
cd "D:\Research C4\backend"
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Keep the terminal running, then open:

- Dashboard: <http://127.0.0.1:8000/>
- API documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

Stop with `Ctrl+C`. Retraining is not required to run the dashboard. There is no separate frontend server.

Once implementation files are included in a checkout, a new computer will need a fresh virtual environment and the packages in `backend/requirements.txt`; do not copy the existing `.venv` between computers.

### Verification evidence

The local implementation passed **26 backend tests**, covering forecast arithmetic, chronological safeguards, source handling, harvest costs, date/water feasibility and editable yield. Browser checks covered source switching, yield changes, excluded/no-eligible options, error recovery and mobile layout. These checks verify prototype behavior, not real-farm effectiveness.

### Remaining work

- Rank eligible dates using farmer-confirmed preferences informed by the survey.
- Introduce explicitly documented risk/loss assumptions and explain the resulting trade-offs.
- Integrate agreed real C1/C2/C3 payloads in place of mock inputs.
- Validate costs, yield assumptions and recommendation usefulness with farmers and domain experts.
- Evaluate forecasts prospectively on newly collected prices.
- Commit the implementation and permitted supporting artifacts to the component branch, then follow the team's integration process.
