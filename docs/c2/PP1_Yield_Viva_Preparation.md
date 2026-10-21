# C2 Yield Prediction: PP1 Viva Preparation

Prepared from current code and saved experiment outputs on **20 October 2026**. Use the [evidence guide](PP1_Yield_Implementation_Evidence.md), [notebook](../../backend/notebooks/c2/yield_research_pp1.ipynb) and [validation record](PP1_Yield_Validation.md) alongside this guide.

## A concise implementation walkthrough

“My responsibility is C2 Predictive Intelligence. For PP1, I built and evaluated a trait-based yield regression prototype using published Capsicum chinense genotype-year aggregates. I use five traits: plant height, main branches, leaf length, leaf breadth and days to 50% flowering. The dataset contains 360 records from 120 genotypes over three years.

“I reserved 18 complete genotypes, or 54 records, for final testing. I used the other 102 genotypes, or 306 records, for five-fold genotype-grouped validation. The preprocessing pipelines fit imputation, and SVR scaling, only on training data. I compared XGBoost, Random Forest, SVR and a simple training-mean reference, then tuned XGBoost on development folds.

“The existing API uses tuned XGBoost, with SHAP analysis explaining its global model behavior. The React page sends manually entered traits to FastAPI and displays the returned estimate and research limitations. SVR had the lowest error on the preliminary held-out test; I do not claim that XGBoost was best. This is not yet a Sri Lankan fresh-yield forecast or live IoT system.”

## Demonstration sequence: about 8–10 minutes

1. **Scope, 1 minute.** State the experimental question and limitations. Open the notebook overview; distinguish aggregate yield estimation from the project's future forecast objective.
2. **Data and split, 2 minutes.** Show 360 rows, 120 genotypes, three years; five inputs; no missing values; 306/54 rows and 102/18 genotypes. Show zero overlap and the fold table. Explain why year records of the same genotype stay together.
3. **Experiments, 2 minutes.** Show original CV results, the 12-candidate tuning output, and selected CV MAE. Then show the separately labeled final-test table. Explain that the test set does not feed back into selection.
4. **Explainability, 1 minute.** Show global SHAP and the beeswarm. State that height ranks highest by contribution magnitude and that this is not a causal effect or an explanation of the next user request.
5. **API/UI, 2 minutes.** With the existing backend running on port 8000 and Vite on 5173, open `/predictions`. Enter **65, 5, 10, 5, 80** in the displayed trait order. Submit; read the actual returned result and warnings. The earlier verification recorded **489.18 g/plant** for these example inputs. Do not present this as a measured plant or a test-set performance score.
6. **Interaction, 1 minute.** Edit an input to show stale results clear; reset; submit empty fields to show validation. Switch MAE/RMSE/R² and expand the saved metric table. Explain that this switches the display, not the serving model.
7. **Finish with next work, 1 minute.** Explain source verification, fresh-mass field data, input timing, future C1 contract and independent local evaluation.

Use the existing environment. Backend command, from `backend/`: `python -m uvicorn app.main:app --reload --port 8000`. Frontend command, from `frontend/`: `npm run dev`. Do not rerun training, tuning, evaluation or SHAP-generation scripts during the demonstration: they write artifacts. For evidence without model files or a running API, show the executed notebook and saved CSV analysis, clearly stating that this is an offline evidence demonstration. Never simulate a successful live response.

VS Code interactive Run All needs a Python kernel package; `ipykernel` is absent in the inspected environment. The supplied runner executes the notebook's Python cells with existing libraries, but is not a Jupyter kernel. Prepare the interactive kernel before the viva if required. Screenshot capture instructions are in the evidence guide.

## Cell-by-cell model training demonstration: optional extra 5–8 minutes

Run the notebook section titled **Model Training Demonstration** by itself in a fresh VS Code kernel. The following sections of the notebook audit original artifacts; you do not need them for this training demonstration.

1. In the controls cell, set `RUN_TRAINING_DEMO=True`. Leave the other two switches false for the short version. Explain that this fits new objects in memory and saves no models or experiment files.
2. Run preparation. Show the five features, separate target, 306 development rows, five saved folds and zero genotype overlap. Say: “Fold 1 is validation, not the final test; these 243 other rows are training.”
3. Run pipeline inspection. Explain that median imputation is in all pipelines, while SVR also has scaling. These are the actual configurations returned by `training.create_models()`.
4. Run XGBoost. Point to `.fit(X_train, y_train)`: “This learns preprocessing and tree parameters from training data.” Then point to `.predict(X_valid)`: “This applies what was learned to validation inputs, without seeing their target values.” Show the fitted median checks.
5. Run Random Forest, then SVR. Explain that each is a fresh clone using the same split. Show the SVR training-fitted scaler table.
6. Run the summary. Say: “These scores were newly computed on development fold 1. They are not the original final-test results.” Interpret MAE/RMSE/R² and avoid claiming model superiority from a single fold.
7. Optionally enable `RUN_FULL_GROUPED_CV_DEMO`, rerun controls and preparation, and run the full-CV cell. It fits 15 pipelines across the saved folds. The three single-fold model cells can be rerun for their summary if needed.
8. Optionally enable `RUN_TUNING_DEMO`, rerun controls and preparation, and run the tuning cell. Explain that this short example samples two candidates from the original parameter space; the recorded original search sampled 12. The fitted winner remains in memory and does not replace the API model.

### What is the difference between `.fit()` and `.predict()`?

`.fit()` learns parameters from training examples and observed targets. For a pipeline, it also learns training-only preprocessing values. `.predict()` takes new inputs and applies those already learned steps. It does not need the new observations' true targets. Those targets are used afterwards to score predictions.

### Are the new demonstration scores another held-out experiment?

No. They are newly executed development validation results. They may match original CV values because the same configurations and folds are used, but they do not provide a new independent test. The optional two-candidate tuning output is a teaching example, not the recorded 12-candidate search. No original CSV or model is updated.

### How do you know the final test was not accessed by the training demonstration?

The section is self-contained, loads only `peerj_development.csv`, and uses its saved validation folds. In verification it was executed in a fresh process with a file-access guard that blocked other datasets, saved models and experiment files. Only the development CSV was opened. The later audit section reads saved held-out results separately; no training cell uses those variables.

## Common examiner questions and accurate answers

### What exactly are you predicting?

The implemented target is `fruit_yield_g_per_plant` for published genotype-year trait aggregates. The units are g/plant, but fresh versus dry fruit mass has not been verified. It is not a prediction of the next seven days' harvest or yield on a specified future date.

### Where did the data come from? Is it Sri Lankan Nai Miris data?

The local source fields identify PeerJ DOI `10.7717/peerj.15521`, India and CSIR-NEIST Jorhat Assam. It is published Capsicum chinense data, not our Sri Lankan field collection. The exact publisher-supplement-to-CSV derivation is not available locally and still needs an audit. The source does not establish local cultivar equivalence or field transfer.

### Are these 360 individual plants?

No. They are 120 genotypes multiplied by three study years. The observation metadata says genotype-year aggregates with published replicates pooled. I cannot treat them as 360 independent plants or recover plant-level variation from the aggregate CSV.

### Why these five predictors?

They provide a small, interpretable set of structural and flowering traits already implemented in the prototype. The current code does not include an ablation study proving they are optimal. Their availability at prediction time must be checked, especially days to 50% flowering. This is a fixed prototype scope, not a claim of optimal feature selection.

### Why exclude fruit count, fruit size, maturity and capsaicin?

Some measurements may only be known late or at harvest; fruit count is also closely connected to yield. Using information unavailable at the intended prediction time could cause leakage. Excluding them is a cautious input-availability choice. It does not mean every such variable is always invalid. A future experiment must specify its prediction cutoff before choosing inputs.

### What preprocessing did you do?

The script validates required columns, genotype-year uniqueness, species and observation type, converts predictors/target to numeric, drops missing targets, rejects negative yields and sorts the records. The current 360 rows have no missing values and none are removed. The fitted ML pipeline includes median imputation, and SVR also includes standard scaling. Those transformations are fitted inside training folds, not on all data beforehand.

### What is XGBoost?

XGBoost is gradient-boosted decision-tree regression. It adds trees sequentially to reduce the chosen loss using gradient information, with regularization to limit complexity. Our tuned model uses 100 trees with depth 2 and learning rate 0.1. It can represent nonlinear relationships and interactions, but it can still overfit or generalize poorly.

### What is Random Forest, and how is it different?

Random Forest builds many randomized trees, typically on bootstrap samples with random feature subsets, then averages their predictions. XGBoost builds trees sequentially to improve the current ensemble. Our fixed forest has 200 trees, maximum depth 6 and minimum leaf size 2. Random Forest had the lowest original grouped-CV MAE here.

### What is SVR?

Support Vector Regression fits a regularized regression function with an epsilon-insensitive error region. Our RBF-kernel SVR can capture smooth nonlinear relationships. C controls the penalty for deviations, and epsilon defines the insensitive region. Scaling matters because kernel distances depend on feature scales. We use C=10 and epsilon=0.1 after training-fitted standardization.

### Why include Training Mean?

It predicts the target average of the training data without learning relationships between traits and yield. It tells us whether the complex models improve on a simple reference. In CV the mean comes from each training fold; in final testing it comes from all development rows. It never uses the held-out target mean for its predictions.

### Why grouped holdout and GroupKFold instead of random rows?

The same genotype appears in three years. Random row splitting could put one genotype in both training and validation/test, giving an overly favorable estimate of transfer to new genotypes. GroupShuffleSplit reserves entire genotypes for testing. GroupKFold keeps entire development genotypes together in each validation fold. There are zero overlapping genotypes across each relevant training/evaluation boundary.

### Does grouped splitting remove every kind of leakage?

No. It addresses genotype overlap. Fold-local preprocessing addresses imputation/scaling leakage. We also exclude the target and guard input timing. But the current split is not chronological or geographic; it cannot prove future-year or new-farm performance. Repeated inspection of a final test can also bias later decisions, so a new external test will be needed for future model selection claims.

### What is the difference between validation and the final test?

The five validation folds come from 306 development records and support comparison/tuning. The final test consists of 54 records from 18 separate genotypes. Its role is to evaluate frozen settings after development. It must not be reused to optimize settings or choose a replacement model and still be called untouched.

### How did you tune XGBoost?

The existing script uses RandomizedSearchCV with 12 candidate settings and negative MAE. PredefinedSplit reuses the exact five genotype-grouped development folds. It searches tree count/depth, learning rate, minimum child weight, subsampling and regularization, then refits the selected pipeline on all development records. The random seed is 42.

### What settings and improvement were selected?

The selected parameters are 100 estimators, depth 2, learning rate 0.1, minimum child weight 1, row and column subsampling 1.0, and L2 regularization 5. Original XGBoost CV MAE is **97.468 g/plant** and tuning-selected CV MAE is **92.901 g/plant**. The search saved MAE only, so I cannot report tuned CV RMSE/R² from that output.

### Can the tuned CV score be optimistic?

Yes. The same validation folds selected settings and supplied the reported winning score. Searching favors settings that did well on those particular folds, including chance variation. Nested grouped CV could separate inner selection from outer evaluation. The existing experiment did not use nested CV.

### Explain MAE, RMSE and R² in simple terms.

For actual yield y and prediction p, MAE is the mean of `abs(y-p)`. RMSE is the square root of the mean of `(y-p)^2`, so large misses matter more. Both are in g/plant. R² is `1 - sum((y-p)^2) / sum((y-mean(y))^2)` on the evaluation set. It compares squared error with predicting that set's mean. R²=1 is perfect agreement; zero matches that reference; negative values can occur. It is not a percentage accuracy score.

### What are your held-out results?

| Model | MAE (g/plant) | RMSE (g/plant) | R² |
| --- | ---: | ---: | ---: |
| Tuned XGBoost | 120.274 | 167.548 | 0.096 |
| Random Forest | 114.499 | 158.717 | 0.189 |
| SVR | 109.857 | 155.793 | 0.218 |
| Training Mean | 137.070 | 176.594 | -0.004 |

These values are verified against the saved metric CSV and recalculated from saved predictions. SVR has the lowest errors on this preliminary holdout. Tuned XGBoost's performance is limited; I do not describe it as high accuracy.

### Why did SVR outperform XGBoost?

The verified fact is the observed ranking. The exact reason is not established by the available experiments. A smooth RBF function, regularization, limited sample size and which genotypes were held out are possible explanations. We did not run a controlled study proving them. I would investigate on development data and assess any new choice on a new untouched test.

### Why still use XGBoost in the API?

It is the planned primary research candidate already implemented with saved tuning and SHAP support. That does not make it the best-performing test model. This task reports the ranking honestly and preserves the current serving configuration. Changing it using this same test result would make the test part of selection; future selection needs an appropriate validation design and independent evaluation.

### Why does Training Mean have negative R² instead of zero?

It predicts the development-set mean. R²'s zero reference uses the actual test-set mean, which can differ. Therefore its test R² can be slightly negative. This does not mean the model predicts negative yields.

### What do the residual plots tell you?

Residual is actual minus predicted. Positive means underprediction; negative means overprediction. A histogram shows the error distribution, and residual versus prediction can reveal systematic patterns or changing spread. Large errors explain why RMSE exceeds MAE. These plots do not provide calibrated uncertainty or prove a particular cause of error.

### What does SHAP do?

SHAP assigns contributions to a model prediction relative to an explainer baseline. In this implementation, TreeExplainer is applied to tuned XGBoost after its fitted imputer on development data. Averaging absolute contributions gives global importance. Height is first at approximately 53.157 g/plant, followed by flowering time, leaf breadth, branches and leaf length.

### Does a large SHAP value mean a trait increases yield?

Not from mean absolute SHAP alone. It measures contribution magnitude and discards sign. The beeswarm shows signed contributions and feature-value coloring across records. Neither proves a causal effect. Correlation between inputs can also affect attribution. An explanation of a model is not proof that changing a trait will change a real plant's yield.

### Does the interface explain my individual prediction?

It displays the submitted measurements and global SHAP evidence. It does not return or compute a per-request local SHAP decomposition. An individual explanation would require a baseline and signed contributions for that exact request; that remains future work.

### Why have Python scripts and a Jupyter notebook?

The existing scripts implement repeatable preprocessing, training, tuning, evaluation and SHAP artifact generation. Their entry points write files and some fit models. The notebook audits saved research evidence and has a separate opt-in Model Training Demonstration. That section imports the existing model factory, fits fresh pipelines on development training rows, predicts development validation rows and shows new results. It can run without the audit cells. It never calls the scripts' artifact-writing entry points or changes a saved model. Scripts are useful for controlled experiment runs; notebooks are useful for inspectable research explanation.

### What is saved in a joblib file? Is JSON the model?

The joblib file contains a fitted Python pipeline: the learned preprocessing state and fitted estimator. The tuned model is `backend/models/c2/yield/xgboost_tuned_development.joblib`; an original XGBoost development model is also saved. JSON stores descriptive metadata and selected settings, not the fitted trees. Only trusted local joblib files should be deserialized. If a model is missing, CSV evidence can still be analyzed, but API inference cannot work.

### Why does metadata say the test was not evaluated?

The JSON was written during training/tuning, before final evaluation, and is not updated by the evaluation script. The later final-test CSVs are the evidence of that evaluation. I interpret the metadata according to its stage instead of claiming no test exists.

### How do FastAPI and React connect?

The React page validates five inputs and the service posts them as JSON to `/api/c2/yield/predict`. Pydantic checks required fields and lower bounds. The endpoint orders features, loads/caches the fitted pipeline and returns a rounded yield estimate, model name, units and research warnings. React validates the response and displays it alongside the submitted values. Static CSV snapshots supply the benchmark and global SHAP panels; those panels do not switch the API's model.

### What testing evidence do you have?

The initial artifact task executed 14 audit code cells and reran eight Node service tests. The training-demonstration update executed all 23 current code cells, including fresh fitting, full grouped CV and the small tuning example. Isolated execution with file-access guards confirmed that training read only the development dataset. The notebook checks split separation, artifact consistency and recalculated scores. The earlier frontend verification document reports a real API/browser flow, responsive checks and accessibility scans; those are attributed prior records, not new browser testing in this task. The separate validation record states the current API/build checks and execution limitations. Unit tests alone do not prove field validity.

### Is the backend ready for any numeric input?

No. Pydantic enforces lower bounds, but does not define empirically justified upper ranges or a full applicability domain. The frontend checks finite inputs, but that does not replace server-side robustness. A numerically accepted request can still lie outside the research data distribution. Structured missing-model handling and stronger server-side finite/range checks are future technical improvements.

### Where are live IoT data, weather and growth stage used?

They are not used in the current five-trait yield pipeline. Inputs are manually entered. Flowering days is a phenological summary, not a dynamic stage model. C1 quality-controlled sensor data, historical weather experiments and C3/C4 integration belong to future work unless separately evidenced. I will not present a planned arrow as a working connection.

### What must happen before a Sri Lankan fresh-yield claim?

We need verified fresh-mass targets, local longitudinal records with plot/plant/genotype identifiers and timestamps, actual harvest dates and weights, management/growth-stage information and calibrated sensor data. We must specify cumulative versus interval yield and prediction horizon, enforce input-availability cutoffs, collect across farms/seasons, and use suitable genotype/farm/time separation. Selection must stay inside development data, followed by an independent local test and uncertainty assessment.

## Keep these distinctions clear

| Accurate statement | Claim to avoid |
| --- | --- |
| Experimental aggregate trait-based estimate | Validated Sri Lankan fresh-yield forecast |
| SVR lowest error on this preliminary holdout | XGBoost is the best-performing model |
| Tuning-selected CV MAE 92.901 g/plant | Independent test error is 92.901 g/plant |
| Global SHAP explains model behavior | SHAP proves causal effects or explains this submitted plant |
| Manual trait inputs and real API inference | Live C1 sensor data is integrated |
| Genotype-separated validation | Future-year/farm transfer is already validated |
| Executed local notebook evidence | Production deployment or supervisor approval |

When evidence is absent, say: “That is not established by the current experiment. My next validation step is …” Then give the relevant concrete step rather than guessing.
