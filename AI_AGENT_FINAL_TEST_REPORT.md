# AI Agent Final End-to-End Test Report

Date: 2026-10-26 (Asia/Karachi). Repository: `D:\Projects 2026\LIfelineTwin`.

## Actual outcome

**Status: LIMITED; live end-to-end success criterion NOT met.** One genuine Groq/LangGraph incident investigation was attempted. Six successful hosted-model responses selected six tool calls, including geographic analysis, environmental observations and the existing TTM forecast. The agent stopped locally before the seventh provider request because its minimum remaining context exceeded the configured input-token estimate ceiling. It did not submit final findings or advisory recommendations.

There was **no Groq HTTP rejection in this run**. In particular, the previous HTTP 413 did not recur in the six requests actually transmitted. This is not proof that the earlier provider limitation is completely resolved: local context admission became the new stopping condition.

No second investigation, diagnostic API request, model substitution or automatic whole-investigation retry was launched. The limited result and full ordered trace were retrieved unchanged after a backend restart.

## Provider, configuration and bounds

| Item | Actual value |
|---|---|
| Provider | Groq |
| Endpoint | `https://api.groq.com/openai/v1` |
| Configured and returned model | `openai/gpt-oss-20b` |
| Token parameter | `max_tokens` |
| SDK/orchestrator | Existing OpenAI-compatible SDK adapter and Phase 4D LangGraph agent |
| Fake/simulated provider used | No |
| Investigations attempted | One |
| Preliminary provider probe | Skipped |
| Provider requests transmitted | Six successful responses; no seventh request sent |
| Provider-call retry used | No |
| Provider attempt limit | Ten, including any allowed transient retry |
| Tool-call limit | Eighteen |
| Overall / analytical deadlines | 240 seconds / 60 seconds |
| Per-provider timeout | Existing 30 seconds |
| Input estimate ceiling | 3,500 tokens |
| Serialized request byte ceiling | 12,000 bytes |
| Output reservation | 1,800 tokens per request |
| Token-per-minute override | Unset; no provider quota guessed |

Provider variables were absent from the current execution session. The previously supplied exact endpoint/model/token settings were applied only to the verification process. The previously supplied credential was entered through hidden terminal input into that process environment, not command arguments or a configuration file. No credential was displayed or written to source, reports, logs or SQLite. The exact credential scan and offline artifact-prefix check both found no credential in saved evidence. Verification processes were stopped after completion.

## Scenario and execution

Evidence directory: `evidence/phase4c-final/live-aj_5_217/`.

- Hypothetical incident ID: `03441472-be07-4aa5-b61a-e58e73a06eab`.
- Agent run ID: `5a311442-c4ec-43fc-a87a-35c1a34c9747`.
- Cached Heidelberg graph: 1,060 nodes and 2,331 directed edges, nine origins and 27 facility records.
- Approved closure scenario: existing betweenness-derived three-segment stress test, excluding Phase 2-selected pairs. No actual infrastructure incident or current closure was asserted.
- A deterministic Phase 4A investigation of the same scenario completed locally for independent comparison. It did not generate additional hosted-model requests.
- The agent was allowed to choose its own tools and sequence, request details and submit the validated final-result tool. No scripted provider or substituted final answer was used.

### Actual model-selected tools

| Model response | Selected tool | Outcome |
|---:|---|---|
| 1 | `retrieve_incident` | Success, attributed incident evidence E1 |
| 2 | `analyze_closures` | Success, actual hypothetical scenario/baseline/restoration output E2 |
| 3 | `retrieve_observations` | Success, real cached environmental estimates E3 |
| 4 | `baseline_accessibility` | Success, baseline output E4 |
| 5 | `retrieve_incident` | Success via reuse of E1; no second retrieval computation or duplicate evidence payload |
| 6 | `generate_forecast` | Success, existing local pretrained TTM prediction E5 |
| Before response 7 | Local context admission | Stopped; no provider request sent |

All six accepted responses identify `openai/gpt-oss-20b`. The trace contains 22 contiguous events: start, context measurements, actual model decisions and tool outputs, then context rejection, classified failure and end. It records tool selection and available source results, not a claim about unobservable internal reasoning.

The model did not call `inspect_evidence` or `complete_investigation` before the local stop. It selected a separate baseline after the scenario already contained baseline values and repeated incident retrieval once. The duplicate incident call reused its original evidence. These are actual model choices, not behaviors concealed by a predetermined workflow.

## Analytical and provenance validation

### Geographic calculations

The live `analyze_closures` result was compared against the deterministic result for the same actual endpoint set:

- Closure endpoint sets equal: true.
- Baseline route records equal: true.
- Before/after accessibility changes equal: true.
- Pair restoration metrics equal: true.

Direct graph reconstruction confirmed:

| Reopened OSM endpoint pairs | Computed origin-metres saved |
|---|---:|
| `(33811019, 928125779)` and `(60697812, 146000024)` | 432.8682130453435 |
| `(33811019, 928125779)` and `(60697818, 298538536)` | 0.0 |
| `(60697812, 146000024)` and `(60697818, 298538536)` | 0.0 |

The verifier uses OSM endpoint pairs and the original accessibility/closure engine, not D1/D2/D3 labels as road identity. These values are real computed tool evidence, not model-generated measurements or accepted final recommendations.

### Environmental estimates and pretrained prediction

- Returned observation values exactly match the deterministic environmental output.
- Source: the existing cached Open-Meteo forecast-API snapshot; this is a historical replay, not a live weather acquisition on October 26.
- These recent-past values are labeled **model-derived environmental estimates**, not verified station observations or evidence of a road closure.
- Eligible context: 740 past hours; 148 future source hours excluded before TTM context preparation.
- Forecast identity: `ibm-granite/granite-timeseries-ttm-r1`, existing local pretrained weights, CPU inference.
- Forecast horizon: 96 hourly values; all forecast values exactly equal the corresponding deterministic Phase 4A prediction.
- No training, fine-tuning or model download occurred. No forecasting accuracy or operational incident causation is claimed.

### Findings and recommendations

There is **no accepted final agent result**, so there are no final findings/citations or advisory recommendations to validate. The verifier's final citation and recommendation-check lists are empty for that reason. Deterministic recommendations and real analytical outputs are not misrepresented as model-submitted final conclusions. Weather/forecast evidence remains isolated from road-status determination.

## Context and provider usage

All six actual provider requests succeeded. Captured SDK usage:

| Request | Estimated input tokens | Reported input | Reported output | Reported total |
|---:|---:|---:|---:|---:|
| 1 | 2,482 | 1,351 | 166 | 1,517 |
| 2 | 2,919 | 1,623 | 385 | 2,008 |
| 3 | 3,217 | 1,855 | 93 | 1,948 |
| 4 | 3,324 | 1,925 | 114 | 2,039 |
| 5 | 3,414 | 1,941 | 88 | 2,029 |
| 6 | 3,429 | 1,941 | 841 | 2,782 |
| **Total** | — | **10,636** | **1,687** | **12,323** |

These are provider-reported token counters, not a monetary cost calculation. Peak transmitted serialized request size was 9,473 bytes. Context strategies included recent-exchange retention and compact recent exchange; no raw assembled prompts were stored in the checkpoint.

Before the next request, the smallest candidate context was:

```json
{
  "request_bytes": 10142,
  "estimated_input_tokens": 3653,
  "reserved_output_tokens": 1800,
  "estimated_reserved_tokens": 5453,
  "max_request_bytes": 12000,
  "max_input_tokens": 3500,
  "strategy": "minimum_context_rejected"
}
```

The byte ceiling was not exceeded; the **estimated input-token ceiling** was exceeded by 153 tokens. That candidate was not sent to Groq, so its true provider token count is unknown.

### Recorded failure classification

- Final run status: `limited`.
- Category: `context_budget`.
- Stage: `context_management`.
- Agent step: 7.
- Completed provider attempts: 6.
- HTTP status / provider code / request ID: null, because this was a local admission decision rather than a provider rejection.
- Transient: false; no retry scheduled or used.

### Assessment of Phase 4D

The optimizations materially reduced transmitted context and allowed six successful model responses, including both weather and forecast tools, without repeating the earlier HTTP 413 in this run. They did **not** achieve end-to-end completion.

The immediate stopping cause is confirmed: minimum context exceeded the locally configured estimate threshold. The observed estimate overcounted all six submitted requests by roughly 1,100–1,500 input tokens. The catalog/archive growth and model's additional/repeated tool choices contributed context, but no single provider quota or root defect is inferred from that alone. The unsent request may also be conservatively overestimated; that is a hypothesis, not permission to assume it would have succeeded. Provider/account rolling limits remain unknown.

No estimator, budget, prompt, orchestration or analytical code was changed during this test to force a passing outcome. No additional probe or investigation was launched.

## Persistence verification

Although the run did not complete, the existing verifier restarted its own localhost backend against the same SQLite file:

- Limited run retrieved unchanged: true.
- Ordered trace retrieved unchanged: true.
- SQLite integrity check: `ok`.
- Trace sequence contiguous: true.
- No assembled raw messages in the checkpoint: true.
- Credential found in saved artifacts: false.

Completed-result persistence is not newly demonstrated by this live test because there was no completed result. The previous 124-test Phase 4D local suite remains the last regression result; it was not rerun and is not presented as a new test execution here.

## Evidence and frontend readiness

Retained files under `evidence/phase4c-final/live-aj_5_217/`:

- `requests.json`
- `summary.json`
- `agent-result-redacted.json`
- `agent-trace-redacted.json`
- `http-transcript-redacted.json`
- `deterministic-result.json`
- `verification.sqlite3`
- `final-test-offline-audit.json`

The verification helper exited 1 to signal incomplete end-to-end verification. No historical result was overwritten or substituted.

**Frontend readiness:** the deterministic backend, real tool integrations, evidence storage and error/status retrieval remain functional. Reliable hosted-agent completion is still an outstanding gate; this run does not justify presenting the live agent as production-ready or consistently completing investigations. Frontend development was not started.

Exactly one live investigation was attempted. All verification servers were stopped. No fake LLM, provider/model switch, new model/training, geographic/forecasting change, Docker/WSL/Zetaris installation, commit or push occurred. Stopped after documenting this actual result.
