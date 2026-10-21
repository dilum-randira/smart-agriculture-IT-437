# C2 Microclimate Forecasting

**Synthetic Data — Prototype Evaluation Only**

The organization below separates preprocessing from the learned-model packages.
Research behavior is unchanged: 336 historical hours, 168 forecast hours, three
targets, frozen chronological partitions, explicit target masks, and train-only
scalers. Soil moisture is an index, temperature is degrees Celsius, and humidity
is percent. Synthetic results do not demonstrate real Nai Miris field accuracy.

```text
microclimate/
  __init__.py
  api/
    schemas.py, service.py, routes.py, demo.py, http.py
    tests/
    README.md
  preprocessing/
    __init__.py
    pipeline.py
    scaling.py
    run_phase1.py
    run_phase1_masked.py
    run_phase1_scaled.py
    tests/{__init__,test_phase1,test_phase1_masked,test_scaling}.py
    README.md, README_masked.md, README_scaled.md
  common/
    __init__.py
    paths.py           # backend paths, source path, SHA-256
    data.py            # frozen scaled NPZ contract and cohort loading
    masked_loss.py     # TensorFlow element masking and epoch accumulation
  models/
    __init__.py
    lstm/
      __init__.py
      model.py
      train.py
      inference.py
      evaluation.py
      reporting.py
      verification.py
      tests/{__init__,test_lstm,test_refactor}.py
      README.md
    gru/
      __init__.py
      model.py, train.py, inference.py
      evaluation.py, reporting.py, verification.py
      tests/
      README.md
    attention_bilstm/
      __init__.py
      model.py, train.py, inference.py
      evaluation.py, reporting.py, verification.py
      tests/
      README.md
  README.md
  <legacy Python wrappers and README redirects>
```

GRU uses the fixed standard baseline architecture; see its [guide](models/gru/README.md).
The primary Attention BiLSTM package is documented in its [guide](models/attention_bilstm/README.md). Preprocessing imports do
not initialize TensorFlow. Only the TensorFlow loss utility imports that framework.
Existing flat module imports, private helper access, and `python -m` entry points
remain supported. Existing test module names remain usable; discovery runs each
canonical test once.

## Commands

Run all commands from `backend/`, using the existing virtual environment.
Preprocessing runners write their documented experiment outputs: these commands
are for deliberate regeneration, and were **not executed during the refactor**.

```powershell
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.preprocessing.run_phase1
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.preprocessing.run_phase1_masked
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.preprocessing.run_phase1_scaled
```

Tests and read-only saved-model verification (logs go outside the experiment):

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s app/c2/microclimate -t . -v
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.lstm.verification --experiment experiments/c2/microclimate/lstm_v1 --evidence-dir "$env:TEMP/c2-lstm-verification"
```

Without `--evidence-dir`, the verification command retains its historical behavior
of refreshing reports in the supplied experiment. Always supply the external path
when inspecting frozen results. Unit tests use disposable fixture models, including
a single optimizer-update test; they never train or alter the research checkpoint.

Future training command, documented only; no training occurred in this refactor:

```powershell
.\.venv\Scripts\python.exe -B -u -m app.c2.microclimate.models.lstm.train --output experiments/c2/microclimate/lstm_v1_reproduction
```

Training requires a new experiment directory and retains the original architecture,
configuration and validation selection. Existing `lstm_v1` is never overwritten.
Frozen inference command, writing a **new** filename in the checkpoint experiment:

```powershell
.\.venv\Scripts\python.exe -B -m app.c2.microclimate.models.lstm.inference --model experiments/c2/microclimate/lstm_v1/lstm_best.keras --input experiments/c2/microclimate/phase1_masked_scaled/windows_test_NODE_01.npz --output experiments/c2/microclimate/lstm_v1/inference_new_NODE_01.npz
```

Inference refuses existing output filenames. That command creates a new artifact;
refactor verification instead used an external temporary checkpoint copy and
read-only comparisons against both saved test prediction files.

## Detailed methods and evidence

- [Complete-case preprocessing](preprocessing/README.md)
- [Target validity masks](preprocessing/README_masked.md)
- [Train-only scaling](preprocessing/README_scaled.md)
- [Standard LSTM](models/lstm/README.md)
- [Standard GRU](models/gru/README.md)
- [Primary Attention BiLSTM](models/attention_bilstm/README.md)
- [Refactor verification](../../../../docs/c2/PP1_Microclimate_Refactor.md)

Datasets, scalers, model files, metrics and plots remain at their existing paths
under `backend/data/c2/microclimate/` and `backend/experiments/c2/microclimate/`.
Keras registered names `c2>MaskedLSTM` and `c2>ValidElementMSE` are unchanged, and
legacy serialization import paths resolve through compatibility wrappers.


The shared FastAPI app now exposes `POST /api/c2/microclimate/forecast` and read-only `GET /api/c2/microclimate/demo-input`. See the [API guide](api/README.md) for the 336-record original-unit request, frozen model selection, quality policy and local Swagger demonstration.
