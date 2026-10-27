# Phase 4B — Agentic Investigation System

Completed: 2026-10-25 (Asia/Karachi). Repository: `D:\Projects 2026\LIfelineTwin`.

**Implemented:** LangGraph LLM/tool orchestration, an OpenAI-compatible standard-SDK provider adapter, validated analytical tools, evidence-bound findings/advisory actions, additive SQLite persistence/checkpoints and agent API endpoints. Phase 4A remains functional.

**Verified:** All **85 tests passed** (previous 67 plus 18 new agent tests). A clearly labeled controlled-fake LLM test exercised real cached Heidelberg and IBM TTM tools over HTTP, compared results with Phase 4A, restarted its own backend process, and retrieved an identical run and trace.

**Not verified:** Genuine live LLM execution. No provider model, endpoint or API key is configured in this environment. The non-fake demo exited 2 with `status=not_configured` and `live_llm_executed=false`; no real LLM call was made. Controlled fake tests are not live LLM or autonomous reasoning evidence.

## Implementation and architecture

New modules under `lifelinetwin_backend/`:

| Module | Responsibility |
|---|---|
| `agent.py` | LangGraph state, conditional LLM/tool loop, bounded calls, exact evidence resolution and per-event persistence |
| `agent_provider.py` | Standard OpenAI Python SDK Chat Completions adapter, explicit environment configuration, no provider/model defaults |
| `agent_tools.py` | Nine registered functions, validated Phase 4A adapters, evidence inspection and server-validated final outputs |
| `agent_limits.py` | Windows spawn subprocess boundaries with enforceable provider/analytical timeouts |
| `agent_schemas.py` | Pydantic API/tool/final-output contracts |
| `agent_storage.py` | Additive `agent_runs` and ordered `agent_traces` tables; restart recovery without automatic API replay |
| `agent_api.py` | New incident-scoped execution/history and run/trace retrieval endpoints |

`main.py` has only additive integration: router registration, a provider-factory injection point for tests, and startup recovery of unfinished agent runs. Existing Phase 4A endpoint contracts, SQLAlchemy tables, deterministic pipeline, analytical modules and cached datasets remain unchanged. No original tests were edited. LangGraph controls the loop via state and conditional edges; there is no scripted baseline-weather-restoration sequence in the production implementation. The model can select tools, inspect evidence, follow up, finish with partial evidence, fail or hit a limit. The controlled test provider uses predetermined responses solely for verification.

Registered function tools:

1. Retrieve this incident and its attributed claims.
2. Retrieve environmental model-derived observations/estimates with provenance.
3. Generate/retrieve the existing pretrained Granite TTM forecast.
4. Compute baseline geographic accessibility.
5. Analyze only caller-approved hypothetical closure subsets.
6. Compare restorations, including relevant two-segment combinations.
7. Retrieve up to five previous Phase 4A investigations for this incident.
8. Inspect successful evidence through bounded RFC6901 JSON-pointer selections.
9. Submit structured final citations/action selections for server validation.

All inputs use Pydantic models with unknown fields forbidden. Existing Phase 4A GeographicResult/EnvironmentResult and investigation schemas validate actual analytical outputs. Incident IDs, weather mode/as_of and endpoint selection are controlled by the API request/configuration; the model cannot override them. Restoration results include exact OSM endpoint pairs in addition to local labels.

## Reliability, evidence and advisory output

- The model never authors accepted distance values, forecasts or closure endpoints. Successful tool calls populate evidence IDs; findings select exact JSON pointers. The backend resolves values from the actual stored tool output. Unknown evidence, invalid pointers, model-provided measurement fields and unsupported action kinds are rejected.
- Actions are advisory, server-rendered templates with citations and `human_review_required=true`. Restoration advice must cite an actual computed alternative with OSM endpoints; environmental review must cite actual environmental evidence.
- Observation estimates, predictions, user-attributed claims, historical investigations and hypothetical geography have distinct evidence categories. An incident's verified label remains submitter attribution. Forecasts never verify a road closure.
- Failed tools do not create successful evidence. They are recorded with bounded error feedback. If the agent later completes using partial evidence, the final result automatically includes `unavailable_evidence` and a mandatory disclosure, even if the model omits it.
- Initial incident/request snapshots, selected tools, validated inputs, full outputs/errors, actual response-model identifiers, timestamps and checkpoints are persisted after events. Decision notes are explicitly untrusted assistant text, not accepted findings or requested hidden chain-of-thought.
- Required provider configuration is validated before creating a run. Missing configuration returns explicit HTTP 503. Later provider failures create a failed run without fabricated findings.
- Maximum bounds are 10 LLM rounds, 20 total tool calls, 300 seconds per run and 60 seconds per analytical call; lower values may be requested. SDK calls are capped at 30 seconds and 1,800 output tokens, with retries disabled. Killable subprocesses enforce provider/tool deadlines, including worker startup. Process cleanup and local SQLite writes can add overhead.
- Successful evidence is capped at 1 MB per run; tool previews at 18,000 characters; individual final/inspection selections at 12,000 serialized characters. Complete outputs remain locally auditable within those limits.
- Incident/source/question text is explicitly untrusted. No terminal, arbitrary filesystem, SQL, browser or model-selected URL tools exist. Closure calls can select only the API request's approved segments. Injection defenses constrain capabilities and outputs; no universal semantic resistance or live-model red-team certification is claimed.
- API keys are read from environment into a SecretStr-backed configuration and passed only to the SDK. They never enter prompts or recorded identities. The configured secret is redacted from persisted strings; raw provider errors are not logged or stored by agent code. Remote LangSmith tracing is disabled around graph execution.

## API and persistence

| Method | Path |
|---|---|
| POST | `/incidents/{incident_id}/agent-investigations` |
| GET | `/incidents/{incident_id}/agent-investigations` |
| GET | `/agent-investigations/{run_id}` |
| GET | `/agent-investigations/{run_id}/trace` |

Started requests return HTTP 201 with a status that must be examined: completed, failed or limited. Missing provider configuration returns 503; invalid input 422; missing incident/run 404; another running agent in the same worker 429. Completed results and traces remain retrievable without provider credentials. Existing Phase 4A routes remain separate and unchanged.

The existing SQLite database is extended with new tables, not replaced. StateGraph runs in memory during execution; sanitized state checkpoints and events are committed using the existing SQLAlchemy layer. On single-instance backend restart, unfinished runs become interrupted, retaining evidence; completed runs remain unchanged. Automatic replay/resumption is disabled to avoid silently repeating provider requests or spending tokens. This is durable recovery for review, not a resumable background job queue.

## Actual test results

Final command:

```powershell
$env:HF_HOME = Join-Path (Get-Location) '.runtime/huggingface'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
.\.venv-migration\Scripts\python.exe -m unittest discover -s tests -v
```

Final observed result: **Ran 85 tests in 135.967s — OK, exit 0, no failures/errors/skips**. Evidence: `evidence/phase4b/full-tests-final.txt` and `full-tests-final-exit.txt`. Expected negative-path application log entries inside tests are not unittest failures.

The 18 new tests in `tests/test_agent.py` are explicitly labeled controlled fake LLM/contract tests. They cover varied tool selection and follow-up calls, real cached baseline execution, structured citation outputs, unknown/unsafe tool rejection, unapproved closures, invented values/citations, provider and real missing-model errors, mandatory unavailable-evidence disclosure, credential redaction including SQLite bytes, missing configuration, iteration/tool/deadline limits, API validation, completed-run/trace persistence, interrupted-run recovery, JSON-pointer resolution, endpoint-bound restoration citations, fixed tool context, registration schemas, and standard SDK request wiring. They do not certify live model behavior.

Initial 14-agent-test run: 14 passed in 35.174s. First expanded regression run: 85 passed in 106.467s. Earlier logs remain separate. Final compilation passed; `pip check` reports no broken requirements.

## Reproducible Heidelberg demonstration — controlled test, real analytical data

Final evidence directory: `evidence/phase4b/controlled-test-of_huagf/`.

- `controlled_fake_test=true`, `live_llm_executed=false`.
- Real cached Heidelberg graph: 1,060 nodes and 2,331 directed edges; nine cached origins and 27 facility records.
- The script derives a scenario through existing betweenness selection, excluding Phase 2-selected pairs. No road outcomes or improvements are hardcoded.
- The controlled test selected baseline accessibility, observations, forecast, restoration comparison, inspection, and final citation submission: 4 model-response rounds and 6 function calls.
- Real existing local TTM weights supplied the prediction; no model was trained or downloaded. The Phase 4A adapter excludes future weather API hours, retaining 740 eligible historical hours and supplying the last 512 to the 96-hour CPU predictor.
- The same incident/scenario was also executed through the real Phase 4A endpoint. Restoration metrics were identical between Phase 4A and the agent's actual analytical tool output.
- The localhost server process was stopped and restarted. Saved agent run and complete ordered trace were exactly equal after restart.
- SQLite integrity check: `ok`. The fresh database contains 1 incident, 1 Phase 4A investigation, 1 environmental output, 2 Phase 4A recommendations, 1 agent run and 12 agent trace events. Agent findings/recommendations are stored in the agent run's structured result.
- Retained artifacts: requests, complete HTTP transcript, summary and SQLite database. An earlier successful controlled test is retained separately.

### Restoration verification by actual OSM endpoints

All values below are graph-computed origin-metres saved relative to the fully disrupted hypothetical scenario, retaining the remaining closure. No new origin is reconnected in these cases.

| Reopened segments (OSM node endpoint pairs) | Computed saving |
|---|---:|
| `(33811019, 928125779)` and `(60697812, 146000024)` | **432.8682130453435 m** |
| `(33811019, 928125779)` and `(60697818, 298538536)` | 0.0 m |
| `(60697812, 146000024)` and `(60697818, 298538536)` | 0.0 m |

The demo independently reconstructs each remaining-closure graph and calls the original accessibility function to verify these metrics. O6's fully disrupted distance is 1,515.304 m versus baseline 749.478 m. The beneficial pair reduces it to 1,082.436 m, not the baseline.

**Historical-report discrepancy:** The preserved Phase 2.5 prose states that reopening both Bismarckstraße segments restores the baseline. The endpoint-based measurements above do not support that statement for this cached graph: the Bismarckstraße pair `(60697812,146000024)` plus `(60697818,298538536)` produces zero saving while the Brückenstraße plus first Bismarckstraße pair yields 432.868 m. This phase documents the measured result and preserves the earlier report rather than silently relying on its explanation. Local D1/D2/D3 labels alone are insufficient evidence.

## Comparison with deterministic Phase 4A

Phase 4A always runs its specified geographic and environmental operations and deterministic recommendation rules. Phase 4B obtains actual provider tool calls and conditionally loops based on their results. It can select subsets and follow-ups, but can also omit evidence, fail, or exhaust its budget. Accepted measurements come from the same analytical functions; the controlled comparison found identical restoration metrics, not superior analysis. Evidence selection/action ranking quality and efficiency against a real LLM remain unverified. The production pipeline's restricted evidence-bound outputs intentionally trade free-form prose for enforceable citation fidelity.

## Provider-dependent blocker and reproduction

No required provider variables are present. The real-mode configuration check produced:

```json
{"status":"not_configured","live_llm_executed":false,"error":"LLM is not configured; set LIFELINETWIN_LLM_MODEL, LIFELINETWIN_LLM_BASE_URL, LIFELINETWIN_LLM_API_KEY"}
```

Configure those variables in the shell that starts the backend using your approved endpoint, exact function-calling model identifier and credential. There are no paid-provider defaults or invented credentials. Remote URLs require HTTPS. `LIFELINETWIN_LLM_TOKEN_PARAMETER` optionally selects `max_tokens` for compatible providers that do not accept the default `max_completion_tokens`. Endpoint-specific compatibility is not yet established.

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
.\.venv-migration\Scripts\python.exe -m pip install -r requirements-phase4b.txt
.\.venv-migration\Scripts\python.exe -m uvicorn lifelinetwin_backend.main:app --host 127.0.0.1 --port 8000
# API schemas: http://127.0.0.1:8000/docs
```

With provider variables configured:

```powershell
.\.venv-migration\Scripts\python.exe scripts/demo_phase4b.py
```

Without provider access, reproduce the explicitly controlled fake test:

```powershell
.\.venv-migration\Scripts\python.exe scripts/demo_phase4b.py --controlled-fake
```

The fake is available only through test/demo factory injection, not through production HTTP arguments or a fallback environment setting. Every demo allocates a fresh evidence directory/database and manages only its own server processes. Full request examples, limits, tool semantics and configuration are in `docs/phase4b-agent.md`.

## Dependencies, preservation and remaining limits

Added LangGraph **1.2.17** and the standard OpenAI SDK **2.54.0**, plus their required transitive dependencies. No unrelated agent framework was added; LangChain-core/LangSmith are LangGraph dependencies. Python remains 3.13.3; existing FastAPI/SQLAlchemy/geographic/IBM/PyTorch dependencies remain in the same environment. `requirements-phase4b.txt` pins additions; `requirements-phase4b-lock.txt` records the full resolved environment. No model download occurred.

Preservation check covers 37 original backend/geographic/test/data files. Only `lifelinetwin_backend/main.py` changed for the additive router/factory/startup integration. Existing analytical code, data, original tests and SQLite Phase 4A tables are unchanged. README gains a Phase 4B link. Prior reports/evidence remain.

Remaining limits: live LLM execution and semantic injection resistance are unverified; provider tokenization/context compatibility may vary; actions are constrained templates; a completed run can be partial; checkpoint recovery does not auto-resume; run only one local worker/server per database; there is no authentication, public deployment, durable queue or frontend. Existing snapshot/centroid/grid-origin/distance/facility limitations apply. The joint Phase 4A environmental adapter requires local TTM even for its observation view. Remote model use sends the selected incident/evidence context to the explicitly configured endpoint; no hidden tracing service is enabled.

No WSL, Docker or Zetaris installation, model training/fine-tuning, frontend, commit or push was performed. Demo servers were stopped. Stopped after Phase 4B implementation and validation, with the live-provider blocker explicitly outstanding.

## Official implementation references

- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling): function definitions, real model tool calls and submitting tool results using the supported API/SDK.
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api): StateGraph state, nodes and conditional looping edges.
