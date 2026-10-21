# C2 PP1 artifact validation

Validation date: **20 October 2026**. All outputs remain local. No dependencies were installed and no artifact-writing training/tuning/evaluation entry points were run. In the additional viva update, fresh development-only model fitting and a small tuning example were explicitly enabled and executed in memory.

## Created artifacts

- [Research notebook](../../backend/notebooks/c2/yield_research_pp1.ipynb): notebook format 4.5, 43 cells (23 executable Python cells and 20 Markdown cells), 31 rendered tables and 10 PNG figure outputs.
- [Notebook execution harness](../../backend/notebooks/c2/verify_yield_research_pp1.py): uses the existing Python environment, executes trusted local notebook cells sequentially and saves their outputs in the notebook. It never calls training entry points.
- [Implementation evidence](PP1_Yield_Implementation_Evidence.md): source links, actual results, implementation details, three Mermaid diagrams and manual screenshot instructions.
- [Viva preparation](PP1_Yield_Viva_Preparation.md): walkthrough, demo sequence, questions/answers and explicit limitations.
- This validation record.

## Fresh checks performed

| Check | Result and limits |
| --- | --- |
| Notebook JSON structure | Format 4.5, unique cell IDs, code/Markdown types, required cell fields, Python parsing, execution counts and output structures checked. Standard `nbformat` validation was unavailable because the package is absent. |
| Complete cell execution | All 23 current code cells passed with `backend/.venv/Scripts/python.exe`, both with default skip controls and with all training/CV/tuning switches enabled; no error outputs. The original audit had also passed from the repository root, notebook directory and temporary directory with the root override. The new training section passed separately in a fresh process without the audit setup or held-out variables. |
| Dataset audit | Original and cleaned data each 360×21; zero missing values and duplicate genotype-year keys; 120 genotypes with three records each; in-memory preprocessing equals saved cleaned data. |
| Split reconstruction | 306 development rows/102 genotypes; 54 test rows/18 genotypes; complete data coverage; no genotype overlap; reconstructed GroupShuffleSplit and all five GroupKFold assignments match saved files. |
| CV outputs | 20 fold metrics and 1,224 out-of-fold predictions checked; targets/genotype order match corresponding validation folds; every MAE/RMSE/R² and fold mean/sample SD recalculated and matched. Training-mean predictions matched each training fold mean. |
| Tuning outputs | 12 candidates; winning parameters and MAE match JSON; search means and population SDs match the five saved search-fold scores. The original 12-candidate search was not repeated; the separately labeled new example sampled two candidates. |
| Final-test outputs | 216 saved predictions, 54/model; actual targets/genotype order match test data; all four models' MAE/RMSE/R² match CSV values. The mean-reference predictions equal the development target mean. No test-driven model selection, held-out refitting or new held-out prediction was performed. |
| SHAP artifacts | Five expected features and nonnegative mean absolute contributions verified; both existing SHAP PNGs decoded successfully and reused. No SHAP recomputation required. |
| Visual review | Inspected all 10 notebook figures in a contact sheet: dataset distribution/year boxplots, trait scatterplots, correlation heatmap, CV comparisons, tuning comparison, held-out metrics, four-model agreement plots, residual diagnostics and two existing SHAP plots. Titles, axes and units are readable. |
| API smoke check | In-process FastAPI TestClient: `/health` HTTP 200; valid prediction HTTP 200; missing fields and zero flowering days HTTP 422. This exercises the actual local fitted model but is not a browser or network-listener test. |
| Prediction example | Inputs height=65, branches=5, leaf length=10, leaf breadth=5, flowering days=80 returned **489.18 g/plant**, `Tuned XGBoost`, with the expected prototype metadata. Demonstration input, not a field reading. |
| Frontend service tests | `npm run test:c2`: 8 passed, 0 failed. |
| Frontend production build | `npm run build`: passed using installed Vite 6.4.4; 55 modules transformed. Build output is local and Git-ignored; no deployment performed. |
| Documentation | Repository-relative Markdown links resolved; three Mermaid blocks checked for consistent structure and agreement with code. Interactive Mermaid rendering was not available in this execution environment. |
| Repository protection | SHA-256 comparison across 83 saved baseline entries found **zero changed original entries**, covering tracked source plus local yield datasets, models and experiments. `git diff --check` passed. New artifacts were separately checked for trailing whitespace and broken local references. |

The original recorded held-out results are XGBoost 120.274/167.548/0.096, Random Forest 114.499/158.717/0.189, SVR 109.857/155.793/0.218, and Training Mean 137.070/176.594/-0.004 (MAE/RMSE/R²; errors in g/plant). These are rounded verified CSV values. SVR has the lowest preliminary test error. XGBoost remains the existing planned primary/API model.

## Additional Model Training Demonstration validation

This update edited **only** the notebook and the three PP1 Markdown documents. The existing notebook runner was reused without modification. No existing source, datasets, saved models or experiment outputs were changed. All new trained pipelines are temporary Python objects, not saved replacements.

The demonstration has nine executable cells: controls, development-data/fold preparation, configuration inspection, XGBoost fitting, Random Forest fitting, SVR fitting, fold-1 summary, optional full grouped CV, and optional small tuning. Ten additional Markdown cells explain those steps before and after execution. The section can run independently in a fresh kernel.

Both default-off execution and explicit opt-in execution passed. The notebook's stored demonstration outputs come from the opt-in run with all three controls enabled. Default controls remain off when no environment switch is set; the printed controls in stored outputs identify the run that produced them.

### Newly executed fold-1 development validation results

These are **NEW DEVELOPMENT-ONLY DEMONSTRATION** results from 243 training rows and 63 validation rows. They are not final held-out metrics and are not written to any experiment CSV.

| Fresh pipeline | Validation MAE (g/plant) | Validation RMSE (g/plant) | Validation R² |
| --- | ---: | ---: | ---: |
| Original-configuration XGBoost | 107.107 | 136.985 | 0.125 |
| Random Forest | 101.794 | 131.351 | 0.196 |
| SVR | 106.680 | 134.622 | 0.155 |

The optional five-fold demonstration fitted 15 fresh pipelines. Its mean MAE/RMSE/R² were XGBoost **97.468/125.007/0.329**, Random Forest **94.932/120.792/0.373**, and SVR **106.261/136.240/0.233**. Agreement with the original CV values reflects reuse of the same configurations/folds in this environment, not new independent evidence. The optional **two-candidate** tuning example produced a selected CV MAE of **94.065 g/plant**; it is distinct from the original **12-candidate** search's **92.901 g/plant**. No demonstration score is used to select against the final test or replace the API model.

### Isolation and artifact protection

A separate validation process executed only the training-section cells, with all switches enabled, from a fresh namespace. A Python file-open audit guard blocked any access within the data/model/experiment directories except read access to `backend/data/c2/yield/processed/peerj_development.csv`; it also blocked writes to that CSV. The recorded dataset access log contained **only that one development CSV**. All model fits, the full grouped-CV branch and the small search completed under this guard. The copied search distributions were also checked against the existing tuning script's AST and matched exactly.

An independent before/after SHA-256 inventory covered 58 existing files in the relevant source, data, model, experiment, notebook and documentation directories. Exactly the four allowed files changed: the notebook and three PP1 documents. The runner and every inventoried non-PP1 file remained unchanged. Git status remains untracked for the PP1 files created earlier in this session; this does not imply existing tracked ML artifacts were replaced.

### Reproduce the enabled run

From the repository root in PowerShell, using the unchanged runner:

```powershell
$env:PP1_RUN_TRAINING_DEMO = '1'
$env:PP1_RUN_FULL_CV_DEMO = '1'
$env:PP1_RUN_TUNING_DEMO = '1'
try {
    .\backend\.venv\Scripts\python.exe backend/notebooks/c2/verify_yield_research_pp1.py
} finally {
    Remove-Item Env:\PP1_RUN_TRAINING_DEMO
    Remove-Item Env:\PP1_RUN_FULL_CV_DEMO
    Remove-Item Env:\PP1_RUN_TUNING_DEMO
}
```

For VS Code cell-by-cell use, set the booleans in the section's controls cell to `True` instead; no environment variable is required. To show just the short training demonstration, enable only `RUN_TRAINING_DEMO`. To guarantee a training-only walkthrough without loading held-out reporting data, run this section alone in a fresh kernel. The full notebook intentionally reads held-out evidence later for the original-results audit, after the demonstration has finished.

## Environment and execution limits

The existing interpreter is Python **3.11.9** in `backend/.venv`. Inspected library versions: pandas **2.3.3**, NumPy **2.4.6**, Matplotlib **3.11.2**, scikit-learn **1.9.1**, XGBoost **3.2.0**, joblib **1.6.0**, FastAPI **0.143.1**. This records the validation environment; it does not establish the original training environment or repair the dependency manifest.

`nbformat`, `nbclient`, `ipykernel` and IPython are absent in this environment. Therefore execution was performed by the supplied Python harness rather than a Jupyter kernel. The notebook has standard Python kernel metadata, ordinary Python cells and MIME outputs; selecting the backend interpreter with an available kernel is the remaining VS Code interactive check. No Colab dependency is introduced. The runner checks essential notebook structure but is not a full nbformat-schema validator. Do not describe this validation as a successful VS Code Jupyter session.

FastAPI TestClient emitted a Starlette deprecation warning about its installed `httpx` integration. The checks still passed. No package replacement or API change was made. The fresh smoke test loaded trusted existing joblib files for inference only; the notebook itself relies on CSV/JSON/PNG evidence and does not deserialize them.

The source article landing page returned HTTP 403 and the PMC page presented a browser challenge. The publisher PDF search result supplied bibliographic/license context; local source metadata and CSVs remain the primary evidence for dataset properties. No original supplementary workbook was available for a complete extraction audit. Supplement-specific rights and the fruit-yield fresh/dry basis remain unresolved; do not infer them from article-level licensing or capsaicin terminology.

The [earlier frontend verification](../../frontend/tests/c2/VERIFICATION.md) records Chromium, responsiveness, accessibility and screenshot checks. Those browser checks were not repeated here. No screenshots, supervisor approvals, field measurements, deployment outcomes or live IoT integration evidence were created or invented.

## Repeat the local audit

From the repository root in PowerShell:

```powershell
.\backend\.venv\Scripts\python.exe backend/notebooks/c2/verify_yield_research_pp1.py
```

With no environment switches set, the command skips demonstration fitting and updates audit/skip outputs only. With explicit training switches enabled, it also fits fresh in-memory demonstration models and records their outputs, without writing model or experiment files. From an unrelated directory, set `$env:PP1_REPO_ROOT` to the absolute repository path and invoke the runner by its absolute path. The notebook can also discover the repository from any descendant working directory. Models remain optional for notebook analysis; the libraries used by imported scoring modules must still be installed in the selected environment.

## Remaining manual tasks

1. Prepare a VS Code Jupyter kernel for the existing interpreter and perform interactive Run All if required for PP1. No environment changes were made automatically.
2. Capture a dated API/UI/notebook screenshot pack using the [evidence guide's instructions](PP1_Yield_Implementation_Evidence.md#manual-screenshot-capture-for-the-pp1-evidence-pack). Include limitations and label example measurements honestly.
3. Review Mermaid diagrams in the Markdown viewer used for presentation.
4. Recover and audit the original supplement/extraction history, confirm fruit-yield weight basis and data redistribution terms.
5. Continue local field-data collection, target/horizon definition and independent validation as research milestones. These are not prerequisites for demonstrating the current prototype, but are required before claiming a validated local forecasting model.

No commit, push, merge, branch/repository setting change, deployment or external publication was performed. Existing ML scripts, fitted models, datasets, experiment outputs, FastAPI code, frontend source and other component code were preserved.
