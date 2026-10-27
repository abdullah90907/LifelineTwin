# Phase 4C — Final Live Agent Verification

Date: 2026-10-25 (Asia/Karachi). Repository: `D:\Projects 2026\LIfelineTwin`.

**Actual result: FAILED; end-to-end success criterion not met.** Exactly one genuine hosted-model incident investigation was attempted. It executed three real tools, then Groq rejected provider attempt 4 with HTTP 413 and code `rate_limit_exceeded`. The new reliability metadata recorded the category, request ID and failing step. No retry or second investigation was launched. The failed investigation and ordered trace were retrieved identically after restarting the backend.

## Provider and scope

| Item | Actual value |
|---|---|
| Provider | Groq |
| Endpoint | `https://api.groq.com/openai/v1` |
| Configured model | `openai/gpt-oss-20b` |
| Actual model on all three accepted responses | `openai/gpt-oss-20b` |
| Token parameter | `max_tokens` |
| SDK / orchestration | Existing OpenAI-compatible adapter and existing LangGraph agent |
| Fake provider used | No |
| Incident investigations attempted | One |
| Preliminary completion/probe requests | None |
| Provider invocations attempted within the run | Four; three accepted responses, one classified rejection |
| Automatic provider retry used | No |

The current process and Windows User/Machine environment did not retain the four provider variables. The exact model, endpoint and token settings previously supplied by the user were set in the verification process. The previously supplied credential was passed through hidden input into that process's environment only. It was not placed in command arguments, configuration files, reports, logs or SQLite. No permanent Windows environment changes were made.

The first launch's automatic permission review timed out before creating a process. The permitted launch retry then started successfully. That launch event was not another investigation or provider request. No additional investigation was launched after the live failure.

## One bounded hypothetical Heidelberg investigation

Evidence directory: `evidence/phase4c-final/live-pj8ogqb2/`.

- Incident ID: `216db365-781b-4fdd-b116-394f7f5856f2`.
- Agent run ID: `fdaa37ab-3f63-423c-8028-b40d53c07f6b`.
- Scenario: explicitly hypothetical, generated from the existing cached Heidelberg graph using the existing betweenness selection and excluding Phase 2-selected pairs. No real closure or incident was asserted.
- Cached graph: 1,060 nodes and 2,331 directed edges; existing nine origins and 27 facility records.
- Bounds: at most 10 total provider attempts, 18 tool calls, 240 seconds overall and 60 seconds per analytical invocation. The existing provider-call 30-second ceiling, 1,800-output-token cap and one run-wide transient retry policy were unchanged.
- A deterministic Phase 4A investigation of the identical approved scenario completed locally for comparison, using existing cached geographic data and TTM assets.
- Final agent status: `failed`, with no accepted structured final result.

### Ordered live trace

| Sequence | Event | Actual outcome |
|---:|---|---|
| 1 | Start | Real configured provider identity; initial incident evidence E0 |
| 2 | Model decision | Actual model selected `retrieve_incident` |
| 3 | Tool | Successful incident retrieval, E1 |
| 4 | Model decision | Actual model selected `baseline_accessibility` |
| 5 | Tool | Successful real baseline analysis, E2 |
| 6 | Model decision | Actual model selected `analyze_closures` |
| 7 | Tool | Successful approved hypothetical closure analysis, E3 |
| 8 | Provider failure | HTTP 413, classified metadata below |
| 9 | End | Run marked failed; no final findings or recommendations accepted |

These were genuine model-selected function calls, not controlled fake responses. The agent received successful tool outputs in the normal LangGraph loop. Its third accepted response selected analysis of the approved closures after the preceding baseline result. No accepted `complete_investigation` call occurred, so final evidence-citation fidelity and advisory recommendation quality were not demonstrated.

## Sanitized failure metadata

Captured at the SDK/subprocess boundary and persisted in the ordered trace:

```json
{
  "category": "provider_request",
  "http_status": 413,
  "provider_code": "rate_limit_exceeded",
  "request_id": "req_01m5t1r65tetssem5vzbed6p1r",
  "transient": false,
  "retry_after_seconds": 36.0,
  "retry_after_supplied": true,
  "stage": "provider_sdk",
  "agent_step": 4,
  "provider_attempt": 4,
  "retry_scheduled": false,
  "retry_decision": "not_transient"
}
```

HTTP 413 is outside the reliability policy's eligible transient statuses (429 with a recognized temporary code, or 500/502/503/504). The code string alone does not make this response retryable. The provider also supplied a 36-second Retry-After; that delay was not slept, shortened or used to launch another request. The existing retry allowance remained unused.

This establishes a provider-side request rejection in this final run. The exact provider quota/token/request threshold was not captured because raw error bodies are intentionally excluded. No extra diagnostic request was made to obtain it. This metadata must not be retroactively attributed to the older Phase 4C failure, whose original classification was lost.

## Numerical grounding and OSM endpoint validation

The successful live `analyze_closures` output was compared with the completed deterministic Phase 4A result for the same approved endpoint set:

- Closure endpoint sets equal: true.
- Baseline route records equal: true.
- Before/after changes equal: true.
- Restoration pair metrics equal: true.

The existing closure-analysis adapter returns before/after and restoration comparisons together; the model did not separately call `compare_restorations`. The verifier also reconstructed each remaining-closure graph and recomputed accessibility with the original engine, identifying roads by endpoint pairs rather than D1/D2/D3 labels.

| Reopened OSM endpoint pairs | Computed origin-metres saved | Direct graph matches deterministic result |
|---|---:|---|
| `(33811019, 928125779)` and `(60697812, 146000024)` | 432.8682130453435 | Yes |
| `(33811019, 928125779)` and `(60697818, 298538536)` | 0.0 | Yes |
| `(60697812, 146000024)` and `(60697818, 298538536)` | 0.0 | Yes |

These are genuine analytical tool outputs available to the agent, not LLM-authored measurements. They were not submitted as final accepted agent findings. The largest pair saving does not restore the full baseline and is not an operational recommendation.

No environmental observation or forecast tool was selected before failure. Phase 4A's local cached TTM prediction completed as part of the deterministic reference, but that result is not claimed as a live-agent forecast. No accepted final citations or recommendations exist to validate. Weather remains unable to establish road closure status.

## Backend restart and evidence persistence

The verifier stopped only its own localhost backend process, launched a new process against the same SQLite database, and retrieved the saved run and ordered trace.

| Check | Actual result |
|---|---|
| Backend process restarted | Yes |
| Saved **failed** investigation retrieved unchanged | Yes |
| Ordered nine-event trace retrieved unchanged | Yes |
| Agent-run row count | One |
| SQLite integrity check | `ok` |
| Trace sequence contiguous | Yes |
| Assembled raw messages retained in new checkpoint | No |
| Credential present in saved verification files | No |
| Completed investigation survives restart | Not demonstrated: this investigation failed |

The final verification helper exited 1, reflecting the failed/incomplete investigation. It did not silently substitute an earlier controlled result or start another run.

## Retained evidence

Under `evidence/phase4c-final/live-pj8ogqb2/`:

- `summary.json` — actual model, limits/outcomes, sanitized failure and analytical checks.
- `requests.json` — hypothetical incident and bounded agent request; no credential.
- `agent-result-redacted.json` — saved failed investigation.
- `agent-trace-redacted.json` — ordered model decisions, actual tool inputs/outputs and sanitized failure.
- `http-transcript-redacted.json` — creation and retrieval before/after restart.
- `deterministic-result.json` — completed local Phase 4A reference.
- `verification.sqlite3` — persistent incident, deterministic result, agent run, evidence/checkpoint and trace.
- `offline-audit.json` — single-run, failure-metadata, privacy and comparison checks.

No artifact from earlier phases was overwritten. The verifier found no credential in the saved files, and the offline audit found no provider-key prefix in the final evidence directory.

## Changes, tests and stopping point

No analytical engine, provider adapter, LangGraph implementation, model or provider was changed. Only the existing verification helper gained a final-run mode to skip the preliminary API probe, isolate evidence, capture the new sanitized failure fields and check recommendation citations when present. It also handles reused evidence outputs from the reliability cache. Python parsed and executed that helper successfully through capture, comparison and restart verification.

The previous local reliability suite remains the last regression result: **108 tests passed in 132.152s**. That suite was not rerun in this verification-only task; it is not presented as a new test execution. The present task's actual validation is the single live run and its offline evidence/restart checks.

The final success criterion is **not met**. Genuine hosted-model tool selection, geographic grounding and failed-run audit persistence were verified. A completed investigation with accepted findings, advisory recommendations and environmental evidence was not produced. There was no automatic whole-investigation retry, follow-up live diagnostic, fake-model substitution, provider/model switch, new model, frontend, Docker/Zetaris/Meterless change, commit or push.

All verification servers were stopped. Stopped after this one attempt and reporting its actual failure.
