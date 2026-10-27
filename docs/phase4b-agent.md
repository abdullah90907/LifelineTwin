# Phase 4B agent investigations

See [Phase 4D context/retrieval and provider budgets](phase4d-agent.md) for the
current optimized context policy and optional quota configuration.

The local [Phase 4C reliability update](../PHASE4C_RELIABILITY_REPORT.md) adds
sanitized failure categories and one run-wide transient retry. The original
Phase 4C live failure remains historical evidence, not a successful verification.

Phase 4A remains available unchanged. Phase 4B adds a LangGraph LLM/tool loop to
the same local FastAPI application and SQLite database. The LLM chooses tools,
inspects results and can request follow-up calls. It does not supply computed
measurements or closure endpoints. The server validates the final citations and
renders advisory action templates. There is no fixed analytical sequence in the
production graph.

## Installation and provider configuration

Use the existing Python 3.13 migration environment and cached analytical assets:

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
.\.venv-migration\Scripts\python.exe -m pip install -r requirements-phase4b.txt
```

Set these environment variables in the terminal that starts the backend. There
is no default provider or model, and no automatic `.env` loading:

| Variable | Value supplied by you |
|---|---|
| `LIFELINETWIN_LLM_BASE_URL` | Your approved OpenAI-compatible Chat Completions endpoint base, including `/v1` if required |
| `LIFELINETWIN_LLM_MODEL` | Exact model identifier offered by that endpoint; must support function calling |
| `LIFELINETWIN_LLM_API_KEY` | Credential for that endpoint; kept in process memory and SDK request headers |
| `LIFELINETWIN_LLM_TOKEN_PARAMETER` | Optional: `max_completion_tokens` (default), or `max_tokens` for compatible providers requiring the older parameter |

Use HTTPS for remote endpoints; HTTP is accepted only on localhost. URL userinfo,
query parameters and fragments are rejected to keep credentials out of URLs.
The API key is not an API request field. Do not paste credentials into incident
descriptions, questions, source text, logs, SQLite or version-controlled files.
Your organization controls endpoint selection and any provider costs. Local
providers may require their own non-secret SDK key value; no value is invented
or silently supplied by this application.

```powershell
.\.venv-migration\Scripts\python.exe -m uvicorn lifelinetwin_backend.main:app --host 127.0.0.1 --port 8000
```

Run a **single worker and single server instance per database**. Startup marks
unfinished agent runs interrupted, retaining their checkpoints and trace. It
does not automatically replay API requests or spend provider tokens again.
Completed runs remain available without a configured provider. This phase is
still a local research application without authentication/authorization.

If any required provider variable is missing, creating an agent investigation
returns HTTP 503 with `code=llm_not_configured`. No agent run is fabricated and no
fallback fake model is installed in the production API. An unavailable provider
after a run begins produces a persisted failed run, with no accepted findings.

## Agent API

| Method | Path | Behavior |
|---|---|---|
| POST | `/incidents/{id}/agent-investigations` | Run an LLM-selected tool investigation synchronously |
| GET | `/incidents/{id}/agent-investigations` | List saved runs (limit/offset) |
| GET | `/agent-investigations/{id}` | Retrieve status, request, configured model identity and validated findings |
| GET | `/agent-investigations/{id}/trace` | Ordered decisions, tool inputs/full outputs, errors and actual response-model identities (limit/offset) |

Example body for an existing incident:

```json
{
  "question": "Compare baseline hospital access and environmental evidence. Explain what remains unverified.",
  "as_of": "2026-10-24T19:55:49Z",
  "mode": "cache",
  "variable": "temperature_2m",
  "allowed_closures": [],
  "max_iterations": 6,
  "max_tool_calls": 12,
  "timeout_seconds": 120,
  "tool_timeout_seconds": 45
}
```

To authorize a hypothetical closure scenario, supply up to six **existing graph
segments** as `{"id":"scenario_label","u":OSM_NODE_ID,"v":OSM_NODE_ID}` in
`allowed_closures`. An empty list permits only baseline analysis. Neither the
model nor an incident description can add closure endpoints. The model chooses
subsets by these approved IDs. All resulting scenarios stay hypothetical even if
an incident contains a submitter-attributed verified claim. Observations and
forecasts never establish road status.

Started runs return HTTP 201 and a status that must be inspected: `completed`,
`failed`, or `limited`. Retrieval may also return `interrupted` after a backend
restart. HTTP 201 alone does not mean a successful investigation. Invalid API
requests return 422, missing incident/run IDs 404, and concurrent agent runs in
one application instance 429. Plain LLM text is never accepted as a final result.

## Tools, evidence and final findings

Nine function definitions have Pydantic-validated inputs:

- Retrieve this incident and its attributed claims.
- Retrieve environmental observations/estimates and their provenance.
- Generate or retrieve the existing Granite TTM prediction.
- Compute baseline hospital accessibility.
- Analyze approved hypothetical closure subsets.
- Compare approved restoration options, including relevant pairs.
- Retrieve up to five previous Phase 4A investigations of this incident.
- Inspect a bounded JSON-pointer value from successful evidence.
- Submit final citation selections for server validation.

The initial incident snapshot is evidence `E0`; successful data tools create
`E1`, `E2`, etc. Complete tool outputs are persisted, while long arrays/paths are
compressed for the model's preview. The model can inspect omitted values with
RFC6901 pointers. Findings cite **original** output paths, not compressed preview
paths. Each finding's value is resolved by the server; a model-supplied value,
unavailable pointer or unknown evidence ID is rejected. Output classifications
distinguish attributed incident claims, environmental model estimates,
pretrained predictions, historical investigations and hypothetical geography.

Final actions use server-controlled advisory templates with citations. A
restoration action must cite a computed alternative containing its actual OSM
endpoint pairs; a weather-review action must cite actual environmental evidence.
Human review is always required. The system intentionally restricts free-form
narrative claims: evidence-backed structured findings are the supported output,
not unconstrained generated incident assertions. A completed run can still be
partial for the question and makes no completeness/optimality claim.

## Limits and security boundaries

- Maximum 10 LLM rounds, 20 total tool calls, 300 seconds per investigation and
  60 seconds per analytical invocation; API clients may request lower values.
- Provider calls are capped at 30 seconds and 1,800 output tokens, with SDK
  retries disabled. The orchestrator may retry once **per entire run** for a
  recognized temporary 429 or HTTP 500/502/503/504. That attempt consumes the
  existing LLM attempt/time budget; it does not enlarge the token cap. Valid
  `Retry-After` values up to five seconds are honored if time remains; longer or
  invalid delays cause the retry to be skipped, never shortened. Timeouts,
  transport errors, quota/authentication failures and malformed calls are not
  automatically retried. Provider and analytical invocations run in killable Windows
  spawn subprocesses. Deadlines include worker startup; process cleanup and
  SQLite checkpoint writes may add overhead.
- A run stores at most 1 MB of successful evidence. Semantic views and the complete
  request budget replace reliance on a per-tool character cap. Final citations
  resolve to at most 12,000 serialized characters; inspections page larger source
  arrays and text without changing the originals. No fabricated values are used.
- Incident text, question text and previous/external evidence are untrusted data.
  System instructions cannot be changed through tool arguments. Tools have no
  arbitrary filesystem, terminal, SQL, browser or user-selected network URL
  capability. The configured provider and fixed Open-Meteo endpoint are the only
  intended external services.
- Provider credentials never enter prompts or stored identities. The configured
  secret is redacted from persisted strings. Raw provider error text is not
  logged/stored by the agent. Decisions record a bounded, explicitly untrusted
  assistant note and selected tools, not requested hidden chain-of-thought.
- New checkpoints retain evidence, attempt/retry counters and a count of messages,
  without retaining assembled raw LLM message payloads. The original API question
  and tool evidence remain in their application/audit records. Older evidence is
  preserved; automatic checkpoint replay is still disabled.
- Repeated identical analytical calls reuse the same evidence ID, including
  normalized ordering of closure IDs; identical failed calls are not executed
  again. The audit records a reference-only event for a repeated call, without
  duplicating the analytical output or rerunning computation.
- Remote LangSmith tracing is disabled around graph execution; SQLite is the
  local audit store. LangGraph's LangChain/LangSmith dependencies are transitive
  requirements, not additional agent frameworks chosen for the implementation.
- Capability and output validation limit prompt-injection impact; no universal
  semantic immunity or comprehensive adversarial security certification is
  claimed. The unauthenticated backend must remain on localhost.

## Reproduction and comparison

Genuine LLM run, **only after configuring the provider**:

```powershell
.\.venv-migration\Scripts\python.exe scripts/demo_phase4b.py
```

The script first validates configuration. If absent, it exits 2 with
`live_llm_executed=false`, without an LLM request. If configured, it uses the real
SDK, generates a reproducible hypothetical Heidelberg scenario from the cached
graph, compares a Phase 4A result with the agent's actual selected tools, restarts
its own localhost server and retrieves the saved agent run and trace.

Controlled fake **test only**, using real graph/weather/TTM tools:

```powershell
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
.\.venv-migration\Scripts\python.exe scripts/demo_phase4b.py --controlled-fake
```

This test uses predetermined LLM responses solely to verify orchestration and tool
integration. Its output explicitly says `controlled_fake_test=true` and
`live_llm_executed=false`. It is not evidence of an autonomous live-model run.
There is no HTTP parameter or environment fallback that enables this provider
in the production application.

Each demo creates a fresh directory and SQLite file under `evidence/phase4b/`,
retaining requests, complete HTTP transcript and summary. It verifies restoration
metrics directly against the original graph using OSM endpoint pairs, never only
labels. A metrics-equality check does not establish that the agent is better:
Phase 4A runs a fixed sequence, whereas Phase 4B can select subsets, follow up,
stop with partial evidence, fail or reach a limit.

```powershell
$env:HF_HOME = Join-Path (Get-Location) '.runtime/huggingface'
.\.venv-migration\Scripts\python.exe -m unittest discover -s tests -v
```

The agent test module is explicitly labeled controlled fake LLM testing. Genuine
provider compatibility/quality remains unverified until a configured model is
successfully exercised. Other limitations from Phase 4A remain, including cached
road topology, snapped origins, model-derived weather, single-centroid weather,
distance rather than travel time, and no operational closure verification. The
existing joint environmental adapter requires local TTM even for its observation
view; missing model assets make those tools explicitly unavailable.
