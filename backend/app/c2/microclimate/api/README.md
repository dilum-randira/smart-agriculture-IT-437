# C2 Microclimate frozen-model API

**Synthetic Data — Prototype Evaluation Only**

This router is registered in the existing `app.main:app`. It performs CPU inference
with frozen LSTM, GRU or Attention BiLSTM checkpoints; it does not train, fit
preprocessing, save models, expose evaluation truth or connect to real C1 hardware.

## Start locally

From the repository's `backend/` directory, using its existing environment:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use one worker for the PP1 demonstration. Model caches are per process; multiple
workers each need their own models. Do not use reload for the stable viva demo.
Swagger UI: `http://127.0.0.1:8000/docs`. Health: `GET /health`.

## Forecast contract

`POST /api/c2/microclimate/forecast`, JSON, maximum **256 KiB** (checked before
JSON parsing, including streamed bodies).

| Field | Contract |
|---|---|
| `model` | `lstm`, `gru`, or `attention_bilstm` |
| `node_id` | `NODE_01` or `NODE_02`, the two prototype nodes; not a model input feature |
| `observations` | Exactly 336 records in chronological, consecutive hourly order |
| `forecast_origin` | Optional explicit origin; if supplied it must equal the last history timestamp |
| `data_origin` | `synthetic` or default `user_supplied_unverified`; a caller declaration, not verified field provenance |

Each historical record contains `timestamp`, `soil_moisture_avg_index`,
`air_temperature_c`, `relative_humidity_pct`. Values must be finite numeric JSON
values (not numeric strings or booleans). Moisture index must be nonnegative;
humidity must be in [0,100], matching existing preprocessing. No invented
temperature or calibrated moisture upper bound is introduced.

Example of **one** record inside the required 336-record array:

```json
{
  "timestamp": "2025-11-07T06:00:00+05:30",
  "soil_moisture_avg_index": 60.23,
  "air_temperature_c": 25.08,
  "relative_humidity_pct": 87.05,
  "record_status": "OK",
  "is_anomaly": false,
  "is_imputed": false,
  "imputed_fields": ""
}
```

Timestamps require an explicit timezone. They are normalized to Asia/Colombo
(UTC+05:30) and must then fall on whole local hours. Equivalent UTC timestamps
are accepted (e.g. `2025-11-07T00:30:00Z` for the record above). Naive times,
duplicates, gaps and out-of-order records are rejected rather than reordered.
Unknown fields, forecast-weather values, `y`, future labels and target masks are
not accepted. No input timestamp can follow the accepted forecast origin.

## Quality policy and scaling

Optional metadata: `record_status` (`OK`, `WARN`, `INVALID`), `is_anomaly`,
`is_imputed`, `imputed_fields` (comma-separated existing source feature names),
and `quality_score` in [0,1]. Imputation flag/field consistency and the source rule
that anomalous/imputed observations cannot be `OK` are enforced.

The original `quality_valid()` rule excludes INVALID, anomalous and supplied-imputed
rows. All three values at excluded rows are replaced only by the last usable
historical values within the supplied request, exactly matching the causal
row-level masking/ffill operation. Clean WARN is usable; there is no new
quality-score threshold. No backward fill or interpolation is performed.

**Leading untrusted history is rejected with 422.** Earlier context outside the
336 records is unavailable, so the API cannot reproduce a fill carried from before
that window. Missing/null/nonfinite core measurements are also rejected, even
when flagged, matching the original dataset validator's finite-value requirement.

Omitted flags default to caller-declared usable observations, not independently
verified genuine measurements. The response reports how many rows included
quality metadata, the declared-quality validity mask and causally filled count,
and states this limitation explicitly. Do not strip flags from demo requests.

The saved **INPUT** scaler transforms `[1,336,3]` in fixed order:
`soil_moisture_avg_index`, `air_temperature_c`, `relative_humidity_pct`.
The frozen model is called with `training=False`; its `[1,168,3]` output is
inverse-transformed with the saved **TARGET** scaler. Scalers are never refitted.
Outputs are not clipped or recalibrated, preserving standalone inference behavior.
Moisture is INDEX, not calibrated volumetric water content; predictions use °C
and % RH (humidity evaluation errors are percentage points).

## Response and chart slices

The response contains the selected model/node, history bounds and quality summary,
last-history forecast origin, 168 predictions with lead hours 1–168 and timezone-aware
future timestamps, fixed feature/target order, units, artifact/scaler SHA-256
provenance and the synthetic-prototype disclaimer. No local filesystem paths are
returned. Future timestamps begin at origin+1 hour, ending at origin+168 hours.

`slices` supplies cumulative 24/72/168-hour boundaries, with `start_index=0` and
`end_index_exclusive=24`, `72` or `168`, plus first/last timestamps. Chart clients
can use `predictions.slice(0, hours)`; no duplicate forecast arrays are needed.

## Read-only PP1 synthetic demo

`GET /api/c2/microclimate/demo-input?model=attention_bilstm&node_id=NODE_01&sample_index=0`

The response has `request` (a complete valid forecast body), `demo` metadata and
`evaluation_label`. It uses a prepared test-window origin, extracts **only its
336 historical rows** from the original synthetic CSV, preserves original quality
flags, and asserts that API preprocessing exactly reproduces that saved scaled X
and history-validity mask. It never reads NPZ y, future targets, target-validity
masks or evaluation predictions for request construction. CSV forecast-weather
fields are not included or used as features. No data is written or regenerated.

Indices 0–810 are available per node. An index whose history starts untrusted is
unsupported by the bounded request contract and receives 422; choose another index.
The two default node histories at index 0 have been verified. No real C1 device,
external weather API, planting date, crop age or growth-stage label is required.

Executable PowerShell example (generates the complete request, not an abbreviated JSON):

```powershell
$demo = Invoke-RestMethod 'http://127.0.0.1:8000/api/c2/microclimate/demo-input?model=attention_bilstm&node_id=NODE_01&sample_index=0'
$body = $demo.request | ConvertTo-Json -Depth 20
$result = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/c2/microclimate/forecast' -ContentType 'application/json; charset=utf-8' -Body $body
$result.predictions.Count   # 168
$result.slices
$result.evaluation_label
```

For Swagger: execute GET demo-input, copy **only its `request` object**, then paste
it into POST forecast's Try-it-out body and Execute. Change `model` to either
other supported identifier to compare frozen models. Do not POST the outer demo
wrapper, omit records, or supply future evaluation actuals.

Complete captured examples and execution evidence are in
`backend/experiments/c2/microclimate/api_integration_v1/`: `demo_request_NODE_01.json`
is a directly POST-able historical body and `example_forecast_response.json` is a
real response, not a hardcoded serving result. The source service always computes
predictions from the selected checkpoint.

## Loading, errors and checks

Artifact locations are resolved from `common.paths.BACKEND`, independent of cwd.
The allowlisted checkpoints are `lstm_v1/lstm_best.keras`, `gru_v1/gru_best.keras`,
`attention_bilstm_v1/attention_bilstm_best.keras`, under the existing experiment root.
The canonical scaler is `phase1_masked_scaled/scalers.json`. Each selected runtime
checks its frozen scaler copy and training provenance before loading registered
Keras objects with `compile=False`. No checkpoints are loaded at application
startup or by demo-input. A lock prevents duplicate concurrent cold loads; each
selected model is cached once, with per-model inference serialization. Importing
shared model classes does not load other models' checkpoints. Restart the process
after any intentionally versioned artifact/configuration update.

Invalid inputs receive sanitized 422 errors without echoing the request or exception
objects; oversized bodies receive 413. Unavailable/incompatible artifacts receive
controlled 503 and inference failures controlled 500. Internal details are logged
only on the server. Yield Prediction validation and serving behavior are unchanged.

```powershell
.\.venv\Scripts\python.exe -B -m unittest app.c2.microclimate.api.tests.test_api -v
.\.venv\Scripts\python.exe -B -m unittest discover -s app/c2/microclimate -t . -v
```

These tests execute real HTTP application routes and all three real checkpoints,
both nodes, original-unit CLI consistency, quality/temporal validation, streaming
body limits, safe errors, cold-load concurrency, repeated-request cache reuse,
cwd-independent startup and the existing Yield Prediction endpoint. Standalone
model verifiers that write reports must run on external copies to preserve frozen
experiments. See the PP1 integration document for actual aggregate results.

This is a local PP1 prototype API, not real IoT integration or evidence of field
accuracy. It supplies point forecasts, not calibrated uncertainty intervals.
