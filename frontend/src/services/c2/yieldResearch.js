import metricsCsv from "../../assets/c2/yield_final_test_metrics.csv?raw";
import shapCsv from "../../assets/c2/shap_feature_importance.csv?raw";
import { yieldFields } from "./yieldApi";

// Fixed-schema aggregate CSV snapshots only; no observation-level data is bundled.
const rows = (csv) => csv.trim().split(/\r?\n/).slice(1).map((line) => line.split(","));
export const benchmarks = rows(metricsCsv).map(([model, mae, rmse, r2]) => ({
  model, mae: Number(mae), rmse: Number(rmse), r2: Number(r2),
}));
export const featureImportance = rows(shapCsv).map(([key, value]) => ({
  key, label: yieldFields.find((field) => field.key === key)?.label || key, value: Number(value),
}));
