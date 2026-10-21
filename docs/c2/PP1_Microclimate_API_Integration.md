# PP1 Microclimate API integration

**Synthetic Data — Prototype Evaluation Only**

Verified locally on October 21, 2026, on branch
`feature/c2-predictive-intelligence`, using `backend/.venv`.
This serves the existing frozen models through the existing `app.main:app`.

## Contract and implementation

`POST /api/c2/microclimate/forecast` accepts `model` (`lstm`, `gru`,
`attention_bilstm`), `node_id` (`NODE_01`, `NODE_02`) and exactly 336
chronological hourly `observations`. Each observation requires a timezone-aware
`timestamp`, `soil_moisture_avg_index`, `air_temperature_c` and
`relative_humidity_pct` in original units. Optional `forecast_origin` must equal
the final history timestamp. Optional `data_origin` describes caller-declared
provenance; it does not authenticate field measurements.

Only these three features, in this order, enter the model. Historical times are
normalized to Asia/Colombo; duplicates, gaps, reordered records, naive times,
nonfinite numbers, unsupported fields and bodies over 256 KiB are rejected.
Future evaluation labels are not accepted as inputs.

Optional quality metadata follows existing preprocessing: INVALID, anomalous and
supplied-imputed rows are excluded and causally forward-filled across all three
features within the request. Clean WARN remains usable. Leading untrusted rows
are rejected because earlier filling context is unavailable. Missing/nonfinite
measurements are rejected even when flagged. Omitted flags mean caller-declared
usable values, not independently verified quality. Responses expose the declared
history-validity mask, metadata coverage and filled-row count.

The saved INPUT scaler transforms `[1,336,3]`; the selected frozen model returns
`[1,168,3]`, then the saved TARGET scaler restores original units. Nothing is
fitted, trained, clipped or recalibrated. Soil moisture remains an INDEX, air
temperature uses °C, and relative humidity uses %.

The allowlisted checkpoints remain at `lstm_v1/lstm_best.keras`,
`gru_v1/gru_best.keras` and `attention_bilstm_v1/attention_bilstm_best.keras` under
`backend/experiments/c2/microclimate/`. The canonical scaler remains
`phase1_masked_scaled/scalers.json`. Paths resolve from the backend location,
independent of the working directory. Existing registered Keras classes are
loaded with `compile=False`; inference uses `training=False`. Provenance and
scaler hashes are checked. A concurrent-load lock and per-model cache prevent
repeated checkpoint loading; each model has an inference lock. Startup and demo
input do not load checkpoints. Restart after an intentional artifact update.

The response includes 168 future predictions, origin+1 through origin+168 hours,
history bounds, units, feature/target order, artifact hashes and disclaimer.
`slices` supplies cumulative chart boundaries `[0,24)`, `[0,72)` and `[0,168)`.
Validation errors are sanitized 422, oversized bodies 413, unavailable artifacts
503 and inference failures 500, without public filesystem paths or tracebacks.

## Start and demonstrate

From `backend/`, use the existing environment and one worker:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`. Execute
`GET /api/c2/microclimate/demo-input?model=attention_bilstm&node_id=NODE_01&sample_index=0`,
copy only its `request` object into POST forecast's Try it out body, then Execute.
Repeat with `lstm` and `gru`.

The demo uses an existing prepared test-window origin and its actual 336
historical synthetic CSV records, preserving quality flags. It asserts exact
equality with the prepared scaled X and history mask. It never reads future y or
target masks to construct requests. Sample indices are 0–810 per node; histories
starting untrusted receive 422. Both default node histories were verified.

Executable request example:

```powershell
$demo = Invoke-RestMethod 'http://127.0.0.1:8000/api/c2/microclimate/demo-input?model=attention_bilstm&node_id=NODE_01&sample_index=0'
$body = $demo.request | ConvertTo-Json -Depth 20
$result = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/c2/microclimate/forecast' -ContentType 'application/json; charset=utf-8' -Body $body
$result.predictions.Count # 168
```

A [complete, directly POST-able JSON request](../../backend/experiments/c2/microclimate/api_integration_v1/demo_request_NODE_01.json)
and [complete actual response](../../backend/experiments/c2/microclimate/api_integration_v1/example_forecast_response.json)
are captured as evidence. The request has `model: "attention_bilstm"`,
`node_id: "NODE_01"`, `data_origin: "synthetic"` and 336 observations from
2025-11-07 06:00 to 2025-11-21 05:00 (+05:30). One actual returned prediction:

```json
{
  "lead_hour": 1,
  "timestamp": "2025-11-21T06:00:00+05:30",
  "soil_moisture_avg_index": 60.25034086665588,
  "air_temperature_c": 24.62260791076761,
  "relative_humidity_pct": 89.68580850988123
}
```

This is a response excerpt, not a full response. The full response carries
`evaluation_label: "Synthetic Data — Prototype Evaluation Only"`.
Captured examples are evidence only; the service computes every forecast from
the selected checkpoint, rather than serving saved predictions.

## Executed verification

| Verification | Passed | Failed/errors |
|---|---:|---:|
| Existing Microclimate tests | 89 | 0 |
| New real-checkpoint API tests | 24 | 0 |
| LSTM saved-artifact checks | 5 | 0 |
| GRU saved-artifact checks | 6 | 0 |
| Attention BiLSTM saved-artifact checks | 8 | 0 |
| **Automated total** | **132** | **0** |
| Additional live Uvicorn HTTP checks | 9 | 0 |

The 113-test discovery suite completed in 69.584 seconds. Artifact suites
completed in 1.270, 134.279 and 149.733 seconds respectively. Verifiers that write
reports ran against external experiment copies; original results were preserved.
All six model/node original-unit comparisons had maximum absolute difference
**0.0**, against a predefined 1e-4 numerical tolerance. Live TCP forecasts for all
three models also matched saved NODE_01 CLI outputs exactly.

Checks covered finite outputs, all 168 timestamps and slices, both nodes,
saved-scaler agreement, metadata handling, invalid requests, safe error paths,
streamed request limits, concurrent cold-load/repeated-request caching,
cwd-independent startup, Swagger/OpenAPI and the existing Yield Prediction API.
Yield Prediction returned HTTP 200 and 275.59 g/plant for its existing valid
example; invalid Yield input still returned 422. The temporary server was stopped.

Re-run the API or combined discovery suite from `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m unittest app.c2.microclimate.api.tests.test_api -v
.\.venv\Scripts\python.exe -B -m unittest discover -s app/c2/microclimate -t . -v
```

Detailed logs, live results, examples and the preservation audit are in
`backend/experiments/c2/microclimate/api_integration_v1/`. See the
[API guide](../../backend/app/c2/microclimate/api/README.md) for the full contract.

## Scope and limitations

No execution blocker remains for the local PP1 demonstration. First inference
loads the requested TensorFlow checkpoint and is slower than cached requests;
each worker has its own cache. Use one worker without reload for the viva.
This local prototype does not provide real C1 integration, field accuracy,
uncertainty intervals, authentication, external weather integration or frontend.
Quality omitted by callers cannot be independently verified. Predictions preserve
the trained models' behavior and are not clipped to physical ranges. No models,
datasets, frozen scalers, previous metrics or unrelated components were changed.
