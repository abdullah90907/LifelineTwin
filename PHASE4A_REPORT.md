# Phase 4A — Integrated Intelligence Backend

Completed: 2026-10-25 (Asia/Karachi). Repository: `D:\Projects 2026\LIfelineTwin`.

**Result:** Functional FastAPI/SQLAlchemy/SQLite research backend. A hypothetical Heidelberg incident was created and investigated over real HTTP; the server process was stopped and restarted, and the saved result was retrieved identically. All **67 tests passed**: the previous 51 plus 16 new backend tests. This is a deterministic tool pipeline, not an autonomous LLM agent.

## Implementation

New package `lifelinetwin_backend/` contains configuration, typed Pydantic schemas (including route and weather result structures), SQLAlchemy tables, existing-tool adapters, deterministic investigation orchestration, and the FastAPI application factory. Startup creates missing tables without deleting data. The application does not depend on Meterless, WSL, Docker or Zetaris.

- Incidents retain title, description, occurrence timestamp, Heidelberg context, status, and separately classified claims: verified, user-reported, or hypothetical. Verified claims require source attribution and a verification method; the backend does not independently certify submissions.
- SQLite stores incidents, investigation requests/results/errors, environmental observation/prediction output and recommendations. Foreign keys are enabled. A completed investigation and its associated rows commit in one transaction. Tool failures are saved as failed investigations; storage failures roll back partial outputs.
- Incidents support create/list/get/status update, history, and observations. Investigations support execution, retrieval and recommendations. Standalone geographic baseline/scenario and environmental endpoints are available. See `docs/phase4a-backend.md` for all paths and example requests.
- The adapter calls existing `data.load`, `accessibility`, `analyze`, `close_segments`, and betweenness selection. Cache checksums are verified by the original loader; there is no geographic download path.
- Individual restoration comparisons remain unchanged. When every individual reopening has zero measurable benefit, all two-segment reopening combinations are computed with the existing graph/routing functions. Remaining closures stay active. Six supplied closures are the limit, bounding pair evaluation at 15 combinations.
- Environmental integration uses existing `load_observations`, `fetch_forecast` and `TTMForecaster`. Cached data remain untouched. Live outputs are stored through investigations in SQLite, without overwriting snapshot files.
- TTM loads only the existing local model snapshot. Missing weights fail explicitly. No model training or additional model download occurred.
- Every result contains the incident/request snapshot, supporting evidence and sources, graph manifest/checksums, actual origin/facility records and snap offsets, model identity/revision/weight hash, timestamps, units, assumptions, limitations and conditional recommendations. Evidence references link recommendations to incident, geography or environmental evidence.

## Environmental time handling and safety

The original weather cache contains both recent-past estimates and future forecast-API values. Phase 4A excludes timestamps later than either the requested `as_of` or the source retrieval timestamp before passing data to TTM. At least 512 contiguous past hourly records are required. Output timestamps are normalized to UTC; the existing forecasting code remains unchanged.

Open-Meteo forecast API recent-past data are explicitly labeled **model-derived estimates**, not verified station measurements. Cache replay is historical and not current conditions or a historically as-issued forecast. The incident timestamp and environmental `as_of` remain separately visible. Weather never selects closures, changes the graph, or establishes that a road is closed. Closure scenarios remain hypothetical even when an incident contains a submitter-attributed verified claim.

## Actual validation

| Check | Actual result |
|---|---|
| Full existing and new suite | **67 tests in 67.111 seconds, OK; exit 0, no skips, failures or errors.** `evidence/phase4a/full-tests-typed.txt` |
| Previous regressions | All original 51 tests included and passing, including real cached graph and pretrained inference. |
| New backend coverage | 16 tests: API contracts/OpenAPI, incident categories, creation/status/history, invalid inputs, missing IDs, failed-tool persistence, atomic rollback, genuine cached TTM/graph integration, restart retrieval, evidence references, future-hour exclusion, timezone normalization, missing-model failure without downloading, short-context failure, pair restoration and pair-skip behavior. |
| Dependency consistency | `pip check`: No broken requirements found. |
| Compilation | Backend package, new demo and new tests compiled successfully. |
| Real HTTP/process restart | PASS, two Uvicorn processes started sequentially using the same fresh demonstration SQLite file; saved investigation exactly equal after restart. |
| SQLite integrity | `PRAGMA integrity_check`: `ok`. Demo contains 1 incident, 1 investigation, 1 environmental output and 2 recommendations. |
| Preservation | SHA-256 comparison of all 29 pre-existing geographic-module, cached-data and test files: no changed or missing originals. Existing evidence and phase reports retained. |
| Live environmental endpoint | `POST /analysis/environment`, mode live: **HTTP 200**. Real Open-Meteo source returned 735 eligible past hourly records; 9 future hours excluded; existing local TTM produced 96 hourly predictions. Response saved in `evidence/phase4a/live-environment-api.json`. |
| No-download cache mode | Genuine cached investigation completed while socket connections were forbidden in the test. Missing model weights produced an explicit failure. Demo server ran with Hugging Face/Transformers offline flags. |

Preliminary runs are retained: initial 12 backend tests passed; an intermediate 63-test suite passed; then the expanded 67-test suite passed. The final run above includes the final typed response schemas. Initial sandboxed API test runs stalled in Windows asyncio's loopback socket setup before executing tests and were stopped; rerunning outside the tool sandbox resolved this. The localhost demonstration's first automatic approval review timed out before launching it; the permitted retry succeeded. These are execution-environment events, not hidden passing test claims.

## Reproducible Heidelberg demonstration

Final demonstration evidence directory:
`evidence/phase4a/heidelberg-demo-08okk56k/`.

The script derives the closure set from the actual cached graph using baseline-used betweenness ranking, excluding the Phase 2 baseline-selected pairs. It does not hardcode road outcomes or a target improvement. The source data have 1,060 nodes and 2,331 directed edges, with nine grid origins and 27 facility records.

Measured results in this explicitly hypothetical scenario:

- O6 distance increases from **749.478 m to 1,515.304 m** (+765.826 m). The other eight origin distances are unchanged, and no origin becomes disconnected.
- All three individual reopenings save **0.0 origin-metres**.
- Reopening **D1+D2 together** saves **432.868213 origin-metres** among already reachable origins. D1+D3 and D2+D3 save 0.0. No pair reconnects an origin. These IDs refer only to this run's computed segments, whose exact endpoints are in `requests.json` and the HTTP transcript; pair evaluation is not claimed to restore the entire baseline.
- The original environmental snapshot supplies **740 eligible past hours**, with **148 future source hours excluded**. TTM consumes the most recent 512 and predicts 96 hourly values. No forecasting accuracy claim is made.
- TTM identity: `ibm-granite/granite-timeseries-ttm-r1`, revision `f04bebdd4c13475b006ce72672e74c9dc28871dc`, **805,280 parameters**, CPU.
- Weights SHA-256: `30f8d9be619518e18c4c15c6ee504e491b9624b48e251661cd5f967bce097731`.
- Persisted incident ID: `0739b1d9-2169-4fad-9fd8-c22deb19fa45`; investigation ID: `81dc11c1-fed0-4cef-9a26-8a0eb2257b10`. Each rerun generates new IDs and a new database.

Files retained: `requests.json`, `http-transcript.json`, `summary.json`, `demo.sqlite3`, `server-first.log`, and `server-restarted.log`. An earlier successful demonstration is also retained separately.

## Dependencies and reproduction

Installed only the backend additions into the existing `.venv-migration` Python 3.13.3 environment:
FastAPI 0.162.0, SQLAlchemy 2.0.55, Pydantic 2.14.1, Uvicorn 0.54.0 and HTTPX 0.28.1, with their required dependencies. Existing geographic/AI dependencies were not upgraded; CPU torch remains 2.11.0+cpu and the existing IBM library revision remains pinned.

`requirements-phase4a.txt` pins backend additions; `requirements-phase4a-lock.txt` captures the complete resolved environment. The local model cache and geographic snapshot must already exist; package installation does not supply them.

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
.\.venv-migration\Scripts\python.exe -m pip install -r requirements-phase4a.txt
.\.venv-migration\Scripts\python.exe -m uvicorn lifelinetwin_backend.main:app --host 127.0.0.1 --port 8000
# API documentation: http://127.0.0.1:8000/docs
```

From a separate terminal:

```powershell
.\.venv-migration\Scripts\python.exe scripts/demo_phase4a.py
$env:HF_HOME = Join-Path (Get-Location) '.runtime/huggingface'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
.\.venv-migration\Scripts\python.exe -m unittest discover -s tests -v
```

The demo manages only its own server on a chosen localhost port and creates a fresh output directory for each run. The normal backend database defaults to `data/backend/lifelinetwin.sqlite3`; set `LIFELINETWIN_DATABASE` before startup to use a different persistent file. The normal server was not left running by this phase. Full API/PowerShell examples and configuration are in `docs/phase4a-backend.md`.

## Limitations and remaining work

- Research/local backend only: no authentication, authorization, frontend, autonomous agent, production deployment, durable job queue, or schema migration framework. Bind to localhost. Use one worker; SQLite is for local workloads and model inference is serialized per application instance.
- Incident coordinates validate membership in the fixed Heidelberg area; routing uses selected existing grid origins, not a new point-specific route. Weather uses the study centroid's returned grid cell, whose actual coordinates are included.
- Network distance is not travel time. Snap offsets, unverified hospital operating/capability status, bounding-box truncation and stale OSM topology remain limitations; no road incident is inferred from those data.
- Restoration comparisons omit costs/capacity and do not search arbitrary larger subsets or claim global optimality.
- Cache mode replays the historical weather snapshot. Live mode depends on Open-Meteo availability and can fail explicitly; there is no silent substitution with stale data.
- A process crash before final persistence does not create a completed investigation; no durable in-progress job recovery is implemented.
- The existing Phase 2.5 CLI printing error and Meterless persistence-reopen limitation remain outside this backend's dependencies and unchanged. The previous migration's absent project branch history remains unchanged.

No application engine code, original data, or original tests were modified. README and .gitignore received additive backend documentation/database-ignore entries. No WSL, Docker or Zetaris installation, paid service, frontend, model training/download, commit, or push was performed. Stopped after Phase 4A.

## Official implementation references

[FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/) and [SQLAlchemy SQLite documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) informed the application/test and SQLite connection patterns. No external framework examples replace the project's existing analytical engines.
