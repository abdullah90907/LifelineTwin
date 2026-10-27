# LifelineTwin

## Current local demonstration

The map-first React/TypeScript application now connects hypothetical disruption
analysis to a saved FastAPI/SQLite investigation: exact OSM endpoints, restoration
comparisons, cached Open-Meteo evidence, local Granite TTM predictions, cited
advisory actions and real Meterless scenario-assumption provenance.

See [run and demo instructions](docs/hackathon-demo.md) and the
[current submission-readiness assessment](HACKATHON_FINAL_READINESS.md).
Zetaris is **not connected**. The demonstrated pipeline is deterministic; a
completed hosted-LLM investigation has not been established by this milestone.

On this already prepared laptop, run these in separate PowerShell terminals:

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
.\.venv-migration\Scripts\python.exe -m uvicorn lifelinetwin_backend.main:app --host 127.0.0.1 --port 8000
```

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin\frontend'
npm run dev
```

Use Node 22.12+ (Node 24 was verified) and the existing Python 3.13 environment.
Open http://127.0.0.1:5173. Existing geographic/weather/model caches are required;
the investigation does not download geography or model weights. Missing Meterless
is explicitly reported and does not disable the analytical pipeline.

The numbered phase sections below are historical records, not the current feature inventory.

## Phase 4B agent investigations

The same backend now supports a LangGraph LLM/tool investigation loop with an
explicitly configured OpenAI-compatible provider, durable tool traces and
evidence-bound findings. See [configuration and API usage](docs/phase4b-agent.md)
and [measured Phase 4B results](PHASE4B_REPORT.md). Without provider configuration,
the API returns an explicit error; controlled fake tests are not live LLM evidence.

## Phase 4A backend

The existing analysis modules are integrated into a deterministic FastAPI/SQLite
incident-investigation workflow. See [backend setup and API examples](docs/phase4a-backend.md)
and [actual Phase 4A results](PHASE4A_REPORT.md). Historical phase text below is
retained. Current frontend functionality is described above.

AI-assisted infrastructure resilience for Open Agent Hackathon 2026. The intended system investigates how road disruptions change access to hospitals and other critical facilities, compares interventions, and explains recommendations.

Research inspiration: adaptive forecasting and lightweight learning under changing conditions (Prof. Zimeng Lyu), and geospatial relationships and agentic spatial services (Prof. Xinyue Ye). This project does not reproduce their published research.

## Phase 1 status

Only technical foundation and sponsor feasibility are in scope. No frontend, maps, forecasting model, or full agent has been built.

- **Meterless:** official reference executes locally; 10 smoke tests, 8 conformance checks, standalone idempotency check, and synthetic road update/provenance test pass. An additional persistence-reopen test fails; see the report before relying on durable state.
- **Zetaris:** blocked, not confirmed. No SQL has executed against Zetaris. Docker/WSL and account-issued distribution are missing; usable machine RAM is substantially below the expected 16 GB.
- No paid infrastructure, purchases, or model downloads.

See [PHASE1_REPORT.md](PHASE1_REPORT.md) for evidence, limitations, and the manual next steps.

## Layout

```text
scripts/           Machine inventory and real Meterless reference integration test
sql/               Proposed Zetaris verification statements (not executed)
docs/              Sponsor setup notes
evidence/          Actual command output and synthetic persisted event logs
vendor/Meterless/  Ignored official sparse checkout, with original Apache-2.0 license
.env.example       Names only; credentials belong in local environment/private files
```

## Local development (PowerShell)

Tested with Node 24.15.0, npm 11.12.1, Python 3.14.4, and Git 2.54.0. Python is used only for the Windows inventory. Meterless needs no Python packages, GPU, model, Docker, or server.

The official source is pinned to `1742dec56a66e58eef9dda2d2b865823758ca8cd`. The existing checkout is ready. To recreate it in a fresh clone of LifelineTwin:

```powershell
git clone --filter=blob:none --sparse https://github.com/Meterless/Meterless.git vendor/Meterless
git -C vendor/Meterless sparse-checkout set engines/world-model
git -C vendor/Meterless checkout 1742dec56a66e58eef9dda2d2b865823758ca8cd
Set-Location vendor/Meterless/engines/world-model/reference
npm ci --no-audit --no-fund
npm test -- --maxWorkers=1
node node_modules/tsx/dist/cli.mjs ../conformance/runner.ts
npm run idempotency-check
Set-Location ../../../../..
npm run test:road
```

Each road run creates a fresh `evidence/road-run-*` directory, preserving earlier runs. It uses the real upstream `WorldModel`, with synthetic inputs clearly marked. The test queries the winning fact for field-level provenance; entity-level provenance alone does not identify the latest status assertion.

```powershell
python scripts/inspect-machine.py
# Additional diagnostic: currently expected to FAIL with exit code 1.
npm run test:road -- --check-reopen
```

Do not interpret the last command's initial in-process PASS block as an overall pass: the subsequent reopen assertion fails. Upstream source was not modified. This is a reference feasibility check, not production readiness or hackathon judging approval.

Credentials must never be pasted into chat or committed. Follow [the Zetaris notes](docs/zetaris-setup.md) once access and hardware are ready. Phase 2 is not authorized.

## Phase 2: geographic intelligence

The Phase 1 text above is retained as historical context. The subsequent user request authorizes Phase 2 only; forecasting, frontend/dashboard work, and Phase 3 remain out of scope. Existing Meterless tests are unchanged, and Zetaris remains a separate blocked integration.

The new `lifelinetwin_geo` Python package measures nearest-hospital driving-network **distance**, applies three **hypothetical** road-segment closures, and ranks independent reopenings. It does not estimate travel time or identify actual incidents. See [the method](docs/phase2-method.md) and [PHASE2_REPORT.md](PHASE2_REPORT.md) for actual results and limitations.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install --only-binary=:all: -r requirements-phase2-lock.txt
# Explicit online acquisition, once; later calls retain the verified cache.
.venv/Scripts/python -m lifelinetwin_geo download
# Offline analysis and tests:
.venv/Scripts/python -m lifelinetwin_geo analyze
.venv/Scripts/python -m unittest discover -s tests -v
```

The engine is in `lifelinetwin_geo/engine.py`; download/cache handling is in `data.py` and the CLI in `__main__.py`. New tests live in `tests/test_geo.py`. `data/heidelberg/` stores the real snapshot and attribution; `evidence/phase2-*` stores outputs. The optional real-data test is explicitly skipped if no complete cache exists; synthetic unit tests alone do not establish real-data completion.
