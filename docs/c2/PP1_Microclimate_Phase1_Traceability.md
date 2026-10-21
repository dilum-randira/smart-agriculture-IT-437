# C2 Microclimate Phase 1 — proposal traceability

**Synthetic Data — Prototype Evaluation Only**

Prepared for the 23 October 2026 PP1 viva. The methodology authority for this
implementation is the proposal specification supplied by the user in this
task; the original submitted proposal document was not independently available
for comparison. No alternate model or forecast definition has been substituted.

| Requirement | Implementation | Executed evidence |
|---|---|---|
| Specified 100% synthetic dataset | `pipeline.load/validate`; runner checks expected rows/nodes | `phase1/validation_report.json`: source SHA-256, 17,520 rows, origins |
| Complete schema and quality audit | Exact 23 columns, types, finite/range/flag checks; node-key duplicates and hourly gaps rejected | JSON missing/status/imputed/anomaly/node counts; malformed-input tests |
| Chronological per-node order | Timezone-aware parsing, Asia/Colombo display, sort by node/time | Timestamp/order/gap tests; origin manifest |
| INVALID and WARN handling | Preserve rows; mask INVALID/anomalous/imputed histories, causal split-local forward fill; clean WARN retained | Quality-policy/forward-fill/no-backfill tests; saved historical masks |
| Chronological split before windows | Common 70/15/15 calendar boundaries, whole input/target within partition | JSON boundaries; split/no-target-crossing tests |
| 336 historical hourly steps | Config default `lookback=336`; three historical core targets | Six NPZ `X` tensors; shape/temporal-alignment tests |
| 168 consecutive future hours | Config default `horizon=168`, stride 1, complete unfilled labels | NPZ `y: [N,168,3]`; manifest and every-real-window alignment test |
| Three exact core targets | Fixed ordered TARGETS tuple | NPZ target names; actual-versus-predicted plots |
| Moisture index, not VWC | Unit string and all documentation | Plot labels, metric units, README |
| No future-target/preprocessing leakage | Input ends at origin, first target is origin+1; no fit or backward fill | Future-perturbation, split-isolation and causal-fill tests |
| Persistence reference | Repeat last usable historical values, 168 steps | Cumulative CSV, lead CSV; independent saved-artifact metric test |
| Cumulative 24/72/168-hour MAE/RMSE | `scores` calculates prefix horizons by node/target/split | 54 cumulative metric rows, sample/value counts; known-error arithmetic tests |
| Lead-time error | Every lead 1..168 independently | 3,024 lead metric rows; `lead_time_mae.png` |
| Actual/predicted timestamps and units | First eligible origin per nonempty cohort; correct +1..168 timeline | Four `actual_vs_persistence_*.png` plots and manifest |
| Reproducible execution/tests | Module CLI and standard-library unittest | README commands; `phase1/test_results.txt` |
| Attention-based BiLSTM primary | Preserved planned model; deliberately not implemented in Phase 1 | Phase 2 pending |
| Standard LSTM and GRU learned baselines | Preserved planned baselines; no replacement estimator | Phase 2 pending |
| Growth-stage-aware future contract | Explicit unavailable growth stage/planting date/crop age metadata | JSON `future_feature_contract`; no fabricated feature columns |
| Exclude unverified forecast weather | Both forecast-weather columns validated but never used in X/y | JSON excluded fields, fixed NPZ feature list |
| Separate external sources | No NASA POWER / ERA5-Land read or join | Pipeline imports and data path |
| No real-field claim | Required disclaimer in metrics, NPZ metadata, reports and all plots | All Phase 1 evidence |
| Preserve Yield/C1/C3/C4/source CSV | New C2-only modules/evidence/docs; input opened read-only | Source hash before/after; Git diff review |

Paths in the evidence column are under
`backend/experiments/c2/microclimate/`. Implementation is under
`backend/app/c2/microclimate/`.

## Explicit implementation choices and blockers

The supplied proposal requirements do not specify split percentages, stride,
quality thresholds, handling of unproven imputations or whether validation
history may cross partitions. The implementation uses a fixed common
70/15/15 chronological calendar, stride one, partition-contained histories,
no additional score threshold and a conservative complete-clean-label policy.
These are documented operational choices, not a replacement forecast
methodology. The current specification's 336/168/3 dimensions are unchanged.

Strict quality filtering leaves NODE_01 with no eligible validation windows
and NODE_02 with no eligible held-out test windows. Thus Phase 1 can provide
only partial node-specific evaluation, and it cannot establish two-node test
performance. Missing scores remain missing, and no example plot exists for
those cohorts. Review the source generator's imputation/anomaly provenance
and the quality policy before Phase 2; keep the frozen split manifest and do
not select alternative boundaries from held-out errors. Phase 2 requires a
reviewed coverage decision and training-only normalization before model work.

Targets are synthetic observations after quality screening, not verified field
ground truth. Overlapping forecasts inflate the number of scored values
relative to unique timestamps. Quality exclusion creates selection bias toward
cleaner intervals. No confidence intervals, sensor calibration, local crop
generalization, real C1 integration, future weather availability or growth-stage
effect is established. The fixed three-channel historical tensor is the Phase
1 core feature set; adding verified growth-stage features later requires a
versioned feature-contract extension while retaining these splits and targets.
