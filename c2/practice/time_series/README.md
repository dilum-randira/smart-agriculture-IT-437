# Practice 02 — Time-Series Forecasting (Google Colab)

**Learning exercise only.** This folder contains *synthetic* hourly temperature, humidity and soil-moisture-like signals created by mathematical formulas. There are **no field readings or observed crop-yield labels** here. No trained-model results are included or claimed until you actually run the experiment.

## Steps (සිංහලෙන්)

1. **Dataset** — `synthetic_weather.py` මගින් පැයකට එක synthetic record එකක් හදනවා. මේවා සැබෑ IoT data නෙවෙයි.
2. **Windows** — `windows.py` මගින් අතීත පැය **48**ක data, ඊළඟ පැය **24** predict කරන්න සකස් කරනවා.
3. **Chronological split** — කාල අනුපිළිවෙළ අනුව train / validation / test. Future target එකක් training වලට යන්නේ නැහැ.
4. **Persistence** — `persistence.py` latest value එක repeat කරලා simple reference එකක් ලබා දෙනවා.
5. **Scaling** — `scaling.py` training input වලින් විතරක් mean/std ඉගෙන ගන්නවා; future data leak වෙන්නේ නැහැ.
6. **LSTM** — `train_lstm.py` train කරලා persistence එක්ක test MAE/RMSE compare කරනවා.

## Run using Colab

Open [Google Colab](https://colab.research.google.com/) → New Notebook → run these cells:

```python
!git clone --branch feature/c2-ml-foundation https://github.com/dilum-randira/smart-agriculture-IT-437.git
%cd /content/smart-agriculture-IT-437
!pip -q install -r c2/requirements.txt
!python -m unittest discover -s c2/tests -v
!python c2/practice/time_series/train_lstm.py
```

Most Colab runtimes already provide TensorFlow. If yours does not, install it in Colab (`%pip install tensorflow`) before the final step. CPU is sufficient for this small exercise; exact training time varies.

**What you should expect:** a test metric comparison for the LSTM and persistence reference. Results depend on actual execution and should not be copied into a research paper as real-farm evidence.

**Research connection:** The proposed C2 model ultimately investigates soil moisture, air temperature and relative humidity with an initial **336-hour lookback and 168-hour output**. This practice uses only **48→24** temperature to learn the pipeline, not to represent the completed C2 primary model. In the research, suitability, timestamp accuracy and measured targets must be validated first.
