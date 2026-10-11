# Practice 02 — Forecast Benchmark Extension (Sinhala guide)

**Practice data only:** All series in this exercise are synthetic, generated from mathematical formulas. They are not IoT field measurements or real Nai Miris research results.

## මෙතෙක් කරපු දේ

- Synthetic weather dataset: **2,880 hourly rows**.
- Past **48-hour** temperature readings to predict next **24 hours**.
- Chronological windows: **324 train / 69 validation / 69 test**.
- User completed a Google Colab LSTM run (20 epochs) and an Actual-vs-Predicted plot.
- User-reported 24-hour cumulative MAE from that practice run: persistence **3.7792°C**, LSTM **0.7800°C**. These results apply only to the synthetic educational example.
- Current script extension adds seasonal-naive baseline and GRU comparison; **GRU and seasonal benchmark results have not yet been reported by the user**.

## Newly implemented concepts

1. `diagnostics.py` — cumulative 6h/12h/24h MAE/RMSE and per-lead errors.
2. `seasonal_naive.py` — repeat the previous 24-hour pattern without training.
3. `compare_recurrent.py` — train **LSTM and GRU** using identical data partitions, training-only scaling and the same training budget.
4. `plot_comparison.py` — observed-vs-predicted figure and per-lead MAE figure.
5. `c2/tests` — unit tests for arrays, splits, scalers, baseline validity and chart generation.

## New Colab session instructions

Open a new Colab notebook and run:

```python
!git clone --branch feature/c2-ml-foundation https://github.com/dilum-randira/smart-agriculture-IT-437.git
%cd /content/smart-agriculture-IT-437
%pip -q install -r c2/requirements.txt -r c2/practice/time_series/requirements-colab.txt
!python -m unittest discover -s c2/tests -v
!python c2/practice/time_series/compare_recurrent.py
!python c2/practice/time_series/plot_comparison.py
```

If the folder already exists in the SAME Colab runtime, instead of re-cloning:

```python
%cd /content/smart-agriculture-IT-437
!git switch feature/c2-ml-foundation
!git pull --ff-only
```

Graphs will be saved under `c2/artifacts/figures/` (intentionally not committed as research evidence). View with:

```python
from IPython.display import Image, display
display(Image(filename='c2/artifacts/figures/practice02_actual_vs_predicted.png'))
display(Image(filename='c2/artifacts/figures/practice02_mae_by_lead.png'))
```

If the TensorFlow run fails because GPU/CUDA is unavailable, continue on CPU. Training results must be observed and checked, not inferred from prepared code.

## Why do these comparisons matter?

- Persistence: දැනට තියෙන අන්තිම උෂ්ණත්ව අගය repeat කරනවා.
- Seasonal naive: ඊයේ තිබුණු පැය 24ක pattern එකම repeat කරනවා.
- LSTM / GRU: historical sequence එකෙන් forecast pattern එකක් ඉගෙන ගන්න learned models.
- **අඩු MAE/RMSE හොඳයි**, නමුත් same test windows මත compare කරන්න ඕනේ.
- Seasonal naive may outperform an LSTM on highly regular synthetic daily patterns. **We measure instead of assuming.**

## Not actual C2 results

Full C2 research still requires auditing public datasets, observing field soil moisture, receiving measured plot-linked fresh Nai Miris harvest labels, and running held-out evaluation at the proposed 24-hour / 3-day / 7-day horizons. An educational 48h→24h temperature experiment does not complete those milestones.
