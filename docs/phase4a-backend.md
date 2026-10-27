# Phase 4A backend

This is a local, synchronous, deterministic research API. It uses SQLite and the
existing Heidelberg, Open-Meteo and Granite TTM modules. No LLM agent, frontend,
Meterless, Docker, WSL, or Zetaris is required.

## Install and run

Use the compatible Python 3.13 environment prepared during migration:

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
.\.venv-migration\Scripts\python.exe -m pip install -r requirements-phase4a.txt
.\.venv-migration\Scripts\python.exe -m uvicorn lifelinetwin_backend.main:app --host 127.0.0.1 --port 8000
```

Open [API documentation](http://127.0.0.1:8000/docs). Bind to localhost: this phase
has no authentication or authorization and is not a public deployment. Use one
worker; inference is serialized per application instance and SQLite is intended
for local workloads. HTTP investigations run synchronously and may take time.

The default database is `data/backend/lifelinetwin.sqlite3`, created on startup
without deleting existing records. The default weather input is the original
888-hour October 24 snapshot. The previously downloaded TTM snapshot must already
exist under `.runtime/huggingface/hub`; missing weights produce an explicit
failure, never a model download. The adapter passes the local snapshot path to
the existing forecaster. Offline cache mode requires no network.

Configuration before starting the server:

```powershell
$env:LIFELINETWIN_DATABASE = 'D:\Projects 2026\LIfelineTwin\data\backend\lifelinetwin.sqlite3'
$env:LIFELINETWIN_WEATHER_SNAPSHOT = 'D:\Projects 2026\LIfelineTwin\data\heidelberg\weather\obs_forecast_2026-10-24_p30_f7.json'
```

Programmatic `Settings` additionally supports alternative geographic/model cache
paths for testing. Defaults resolve against the repository, independent of cwd.
No `.env` file is automatically loaded.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | SQLite connectivity and presence of cache/model files (not full readiness validation) |
| POST / GET | `/incidents` | Create/list incidents; list supports limit/offset |
| GET | `/incidents/{id}` | Retrieve incident, context and attributed claims |
| PATCH | `/incidents/{id}/status` | Set open/investigating/resolved |
| POST / GET | `/incidents/{id}/investigations` | Run investigation / view persisted history |
| GET | `/investigations/{id}` | Retrieve completed or failed investigation |
| GET | `/incidents/{id}/observations` | Persisted environmental outputs, linked to investigation |
| GET | `/investigations/{id}/recommendations` | Persisted conditional actions |
| GET | `/analysis/baseline` | Baseline accessibility; empty closure set |
| POST | `/analysis/geographic` | Explicit hypothetical closures or betweenness stress-test selection |
| POST | `/analysis/environment` | Cached or live Open-Meteo context and local pretrained TTM prediction |

Unknown fields, naive datetimes, out-of-bounds coordinates, unsupported variables,
duplicate segments, invalid status and malformed UUIDs return 422. Missing records
return 404. Failed tool calls return 503 (or 422 for analytical input errors) and
include a persisted investigation ID when launched through an incident. No
partial environmental/recommendation rows are saved for failed investigations.
SQLite storage failures roll back the transaction and return a server error.

## Create and investigate a hypothetical incident

```powershell
$incident = @{
  title = 'Hypothetical Heidelberg disruption'
  description = 'Research scenario only; no real road closure asserted.'
  kind = 'hypothetical'
  occurred_at = '2026-10-24T19:55:49Z'
  context = @{ latitude = 49.415; longitude = 8.6775; origin_ids = @() }
  claims = @()
} | ConvertTo-Json -Depth 6
$created = Invoke-RestMethod http://127.0.0.1:8000/incidents -Method Post -ContentType application/json -Body $incident
$request = @{
  as_of = '2026-10-24T19:55:49Z'
  mode = 'cache'
  variable = 'temperature_2m'
  selection = 'betweenness'
  count = 3
} | ConvertTo-Json
$investigation = Invoke-RestMethod "http://127.0.0.1:8000/incidents/$($created.id)/investigations" -Method Post -ContentType application/json -Body $request
$investigation.result.recommendations
```

For an explicit scenario use `selection='provided'` and
`closures=[{"id":"label","u":OSM_NODE_ID,"v":OSM_NODE_ID}, ...]`.
Empty closures mean a baseline, never automatic weather-driven closures. At most
six segments are accepted. Betweenness selection through an incident is permitted
only when the incident itself is hypothetical. This is a stress test, not an
incident detector. Incident location must be inside the fixed study area; routes
use the cached grid origins, optionally filtered by `origin_ids`, rather than
snapping a new origin at the incident coordinates.

Kinds `verified`, `user_reported`, and `hypothetical` are stored separately on
incidents and claims. A verified incident requires an attributed verified claim
with a verification method. This records what the submitter supplied; the API
does not independently verify the source or confer operational authority.

## Reproducible demonstration and tests

```powershell
.\.venv-migration\Scripts\python.exe scripts/demo_phase4a.py
.\.venv-migration\Scripts\python.exe -m unittest discover -s tests -v
```

The demo creates a fresh evidence directory and SQLite file, derives a three-link
stress test from betweenness while excluding the baseline Phase 2 selections,
uses real cached environmental data and pretrained inference, creates an incident
through a real HTTP server, terminates its own server process, restarts it with
the same database and verifies identical saved output. Both server logs, the HTTP
transcript, requests and summary remain under `evidence/phase4a/heidelberg-demo-*`.
No results are hardcoded. The entire application process is restarted, including
the SQLAlchemy engine. No user-owned server is terminated.

## Interpretation and limits

Only source hours at or before both `as_of` and the source retrieval timestamp
enter TTM context. At least 512 contiguous past hours are required. Future
forecast-API hours are excluded. Cache mode is historical snapshot replay, not
live conditions or a historically as-issued prediction. Open-Meteo forecast API
recent-past values are model-derived estimates, not certified station measurements.
Live mode calls the existing ingestion function and stores the resulting output
only in the new backend database; existing snapshot files are not overwritten.
All outputs retain timestamps, units, retrieval/source identity, cache hash, model
revision, weight hash and explicit assumptions. The incident time and requested
environmental `as_of` remain separately visible; no causal link is inferred.

Weather never changes routing topology. Recommendations use graph measurements
and remain conditional on verified road conditions. Distances omit snap offsets,
external facilities, traffic, turn restrictions, facility operating status,
population weights and restoration costs. If every individual reopening has zero
benefit, the adapter evaluates all two-segment combinations, leaving the other
closures active. This adds comparisons, not a new routing algorithm. No claim of
global optimality is made for larger combinations.

The pipeline has no durable job queue, cancellation, multiuser access control,
schema migration framework or automatic retries. A process crash before the final
transaction commits cannot leave a completed investigation. Completed records are
immutable snapshots even if incident status later changes.
