# C2 Microclimate organizational refactor verification

**Synthetic Data — Prototype Evaluation Only**

Completed on branch `feature/c2-predictive-intelligence`, using `backend/.venv`, Python 3.11.9. No research model training, package installation, dataset or artifact regeneration, commit or push occurred.

## Final structure

See the complete [package tree and commands](../../backend/app/c2/microclimate/README.md). All datasets, trained models, scalers, metrics and plots retain their original locations.

## Implementation moves

Each original path below remains a thin forwarding wrapper. The canonical implementation exists only at the destination. All paths are relative to `backend/app/c2/microclimate/`.

| Original compatibility module | Canonical implementation |
|---|---|
| `pipeline.py` | `preprocessing/pipeline.py` |
| `scaling.py` | `preprocessing/scaling.py` |
| `run_phase1.py` | `preprocessing/run_phase1.py` |
| `run_phase1_masked.py` | `preprocessing/run_phase1_masked.py` |
| `run_phase1_scaled.py` | `preprocessing/run_phase1_scaled.py` |
| `test_phase1.py` | `preprocessing/tests/test_phase1.py` |
| `test_phase1_masked.py` | `preprocessing/tests/test_phase1_masked.py` |
| `test_scaling.py` | `preprocessing/tests/test_scaling.py` |
| `lstm_model.py` | `models/lstm/model.py` |
| `train_lstm.py` | `models/lstm/train.py` |
| `infer_lstm.py` | `models/lstm/inference.py` |
| `lstm_evaluation.py` | `models/lstm/evaluation.py` |
| `lstm_reporting.py` | `models/lstm/reporting.py` |
| `verify_lstm_artifacts.py` | `models/lstm/verification.py` |
| `test_lstm.py` | `models/lstm/tests/test_lstm.py` |

Created eight package initializers: preprocessing, preprocessing/tests, common, models, models/lstm, models/lstm/tests, models/gru and models/attention_bilstm. GRU and Attention BiLSTM contain only initializers. The original root initializer is unchanged.

Created `common/paths.py` (stable backend/source/scaled experiment paths and SHA-256), `common/data.py` (unchanged frozen scaled NPZ contract and node/cohort loaders), and `common/masked_loss.py` (unchanged TensorFlow masked SSE/count and ValidElementMSE accumulator). These are shared forecast utilities; no model architecture or new preprocessing was introduced. Preprocessing imports do not import TensorFlow.

Created `models/lstm/tests/test_refactor.py` with five compatibility tests. Detailed READMEs moved to `preprocessing/README.md`, `preprocessing/README_masked.md`, `preprocessing/README_scaled.md` and `models/lstm/README.md`. Root README is the overview; old named README paths redirect. Updated commands in the four existing Microclimate PP1 documents; no Yield documentation changed.

The verifier accepts an optional external `--evidence-dir`; with this option it writes logs externally and does not refresh experiment reports. Its historical no-option behavior is preserved. Added callable CLI main functions and safe help parsing for the moved runners so wrappers never duplicate implementations.

## Executed verification

| Check | Result |
|---|---|
| Canonical unittest discovery | 69 passed, 0 failed, 0 skipped; final run 18.129 seconds |
| Existing tests via legacy module paths | 64 passed, 0 failed, 0 skipped |
| Saved LSTM integration suite, external logs | 5 passed, 0 failed |
| Full inference and Yield/FastAPI regression suite | 5 passed, 0 failed; 131.730 seconds |
| Total distinct automated tests/checks | 79 passed, 0 failed |
| Preprocessing imports without TensorFlow initialization | Passed |

The 69 discoverable tests comprise 54 preprocessing tests, 10 existing LSTM tests and 5 new refactor tests. The repeated legacy run is not added to the distinct total. The existing optimizer unit test updates a disposable fixture once; it does not retrain the saved research model. No separate pre-existing Yield Python test suite was found. Regression checks imported all Yield Python modules, executed the saved XGBoost prediction (275.59 g/plant for the fixed smoke-test input), and exercised `/health`, `/openapi.json` and `/api/c2/yield/predict` through FastAPI TestClient.

The preserved 13,027-parameter checkpoint reloads with `compile=False`. Full reloaded predictions for NODE_01 and NODE_02 both have shape `[811,168,3]`. Maximum absolute difference from saved predictions is **0.0**, both scaled and inverse-transformed original units. The unchanged inference function was also executed on all NODE_01 test windows using an external temporary checkpoint/scaler copy; outputs and timestamps match the saved results. No new inference output was written into the frozen experiment.

Function/class AST comparison confirms identical preprocessing, scaling, masked loss, model architecture, inference and metric bodies after relocation/extraction. Training function differences are canonical import/test-module references only; training configuration, layers and optimization are unchanged. Registered serialization names remain `c2>MaskedLSTM` and `c2>ValidElementMSE`, and old module imports resolve to the same classes.

## Preservation and audit evidence

External pre-refactor source backup, repository hash inventory, source diff, test logs and inference comparisons:

`C:\Users\Asus\AppData\Local\C2RefactorAudit\20261021-163305`

166 pre-existing files outside the Microclimate source package were checked. Four authorized Microclimate documentation files changed; all other 162 files remain byte-identical. No files are missing. This includes all protected data, experiment artifacts, Yield source/model/results, FastAPI entry point and other existing components.

`lstm_best.keras` SHA-256:

`4194e6a8f3eb104ffa9b689373db1f2f5c3eb0ed05e93d17e362c8c49988e855`

`git diff --check` passes and there are no tracked-file changes. The Microclimate source/data/experiments, notebooks and docs directories were already untracked before this task; therefore preservation was checked using the external pre-refactor hashes and a `git diff --no-index` source comparison as well as Git status. No staging was performed.

## Commands and remaining issues

Exact preprocessing, training, inference and read-only verification commands are in the [package README](../../backend/app/c2/microclimate/README.md). Training and preprocessing regeneration commands were documented only. Existing flat `python -m app.c2.microclimate.*` entry points remain usable.

No broken imports or compatibility blockers remain. Existing environment warnings concern native-Windows TensorFlow CPU operation, Keras/NumPy array conversion, Starlette/httpx and SHAP deprecations; no packages were changed. Inference still requires a new output filename inside the chosen checkpoint directory, and the verifier refreshes reports unless an external evidence directory is supplied. Synthetic evidence does not establish real-field forecasting accuracy.
