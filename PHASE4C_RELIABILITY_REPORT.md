# Phase 4C Reliability Report

Date: 2026-10-25 (Asia/Karachi). Repository: `D:\Projects 2026\LIfelineTwin`.

**Result:** Local reliability fix implemented and verified. **108 tests passed**: all previous 85 tests plus 23 new reliability tests. **No live provider requests were made.** The historical live Groq investigation remains failed; this task does not claim a new successful live investigation or retrospectively identify its unknown failure cause.

## Reproduced loss of classification

Inspected `PHASE4C_REPORT.md`, the saved eight-event redacted trace from `evidence/phase4c/live-q4pmoaf9/`, the SDK adapter, LangGraph loop, subprocess handling and SQLite checkpoint implementation.

The loss occurred at two boundaries:

1. `agent_limits._worker` converted every exception to only its class name, discarding available SDK HTTP status, provider code, request ID and retry headers. `bounded_call` then reconstructed an ordinary RuntimeError.
2. `AgentRunner.llm_node` caught the result generically and stored a single undifferentiated error. Invalid responses, rate limits, transport failures and timeouts were not individually auditable.

Before editing those paths, two offline tests raised an actual SDK RateLimitError containing a synthetic 429 response and sensitive dummy body. The tests reproduced the defect: one failure and one error, with the worker returning only `{'ok': false, 'error_type': 'RateLimitError'}`. No network request was involved. Original reproduction output is retained in `evidence/phase4c-reliability/reproduction-before.txt`.

The historical trace has three accepted real-model decisions and three successful tools, followed by the generic failure. It contains no recoverable HTTP classification for the failed invocation. Nothing in the local tests establishes whether that original failure was a rate limit, malformed call, timeout or transport problem.

## Changes

### Sanitized metadata across the subprocess boundary

New `lifelinetwin_backend/agent_failures.py` defines a validated failure envelope. The worker sends this envelope instead of raw exceptions or exception messages. `bounded_call` reconstructs a classified failure. The provider adapter also classifies an invalid SDK response shape and retains a safe response request ID.

Metadata retained where available:

- Failure category and stage.
- HTTP status.
- Allowlisted provider error code.
- Validated request ID (supported request-prefixed IDs or UUIDs).
- Whether a Retry-After header was supplied and its parsed delay.
- Transient classification.
- Failing agent step, provider-attempt number, retry decision and whether a retry is scheduled.

Exception messages, arbitrary body fields, failed-generation text, request bodies/prompts, raw headers and credentials are not copied into failure records. Unknown provider codes and unsafe request identifiers are omitted rather than stored as arbitrary external strings. The existing configured-secret redaction still applies before persistence. Authentication/permission errors, hard quota failures, service failures, rate limits, SDK timeouts, transport failures, malformed tool calls, invalid agent outputs, invalid tool arguments and worker failures are separately classified.

Provider failure events are available through the existing ordered trace API; no SQL schema migration or new API route is required. Tool failures carry their own category and failing step/call number. Existing accepted evidence remains in the durable checkpoint.

### At most one bounded retry per entire investigation

The retry is in the orchestrator, not the SDK. SDK retries remain disabled.

| Failure | Automatic retry policy |
|---|---|
| HTTP 429 with a recognized temporary rate-limit code | Eligible once, if budgets permit |
| HTTP 500, 502, 503 or 504 | Eligible once, if budgets permit |
| Hard quota, unknown 429 classification, authentication/permission or other permanent request errors | No retry |
| SDK timeout, parent subprocess timeout, or transport failure | No retry; whether generation occurred may be ambiguous |
| Groq `tool_use_failed`, malformed tool-call envelopes or invalid JSON arguments | No retry |
| Invalid tool arguments or final evidence/citation output | No transport retry or automatic analytical replay |

Retry-After accepts finite nonnegative seconds and HTTP dates. A valid delay of at most five seconds is honored only if at least one second of call budget remains afterward. Longer, invalid or unaffordable supplied delays cause the retry to be skipped, **not shortened**. When no header exists, the backoff is 0.25 seconds. The trace records why a retry was scheduled or skipped.

There is one retry allowance for the **whole run**, not one per step. Every provider invocation, including failed and retried attempts, consumes the existing `max_iterations` attempt budget. The original run deadline and per-call deadline apply to the retry. The 1,800-output-token ceiling per invocation is unchanged, so the maximum run allowance remains at most `max_iterations × 1,800` output tokens; no extra token/iteration allowance is added for retrying. Actual provider billing for failed calls cannot be guaranteed by the client.

The retry reuses the same in-memory messages at the failing LLM step. It does not rerun earlier tools, reset the graph or create a second investigation. Existing bounded model-directed input correction is still possible after tool-validation feedback, but the reliability retry mechanism never replays an invalid tool call.

### Prevent duplicate analytical work and logical writes

A per-run cache keys validated analytical requests by tool name and canonical arguments. Closure IDs are sorted for cache identity, so requesting the same subset in a different order does not trigger recomputation.

- Repeated successful calls reuse the original evidence ID and output.
- Repeated identical failed analytical calls do not execute again.
- Duplicate trace entries contain a reuse flag and evidence reference; they do not duplicate the full analytical payload.
- No duplicate evidence record or second investigation/result row is created by a retry or duplicate tool request.
- Small ordered audit/checkpoint updates are intentionally retained; suppressing those would hide that the model requested a repeated call.

Source evidence is immutable during retry. Corrected, genuinely different model-selected arguments may still cause a new bounded analysis. Cache state is preserved in the checkpoint, but backend restart still marks unfinished runs interrupted rather than automatically replaying requests.

### Prompt and credential handling

New checkpoints retain evidence, tool-cache references, status, attempt/retry counters and message count, **without storing assembled raw LLM message payloads**. The original API question and ordinary incident/tool evidence remain in their existing application/audit records; they are not duplicated as SDK prompts. No new provider error logging contains raw prompts or provider bodies.

Historical traces/checkpoints were preserved byte-for-byte; no old record was rewritten or deleted. Completed-run retrieval and evidence audit remain functional. Automatic checkpoint replay remains disabled. A future diagnostic requiring an exact new-run prompt must reconstruct context explicitly; it cannot obtain an assembled raw prompt from these new checkpoints.

## Controlled example actually executed

`evidence/phase4c-reliability/controlled-retry-example.json` records an **offline controlled test**, not a live model result:

1. A controlled model response requests incident retrieval; one analytical result becomes evidence E1.
2. The next invocation simulates an SDK HTTP 429 with a temporary rate-limit code and a two-second Retry-After.
3. The single retry succeeds and submits citations to the original accepted evidence.

Observed: 3 provider attempts, **1 analytical execution**, one scheduled two-second delay (sleep mocked in the test), one investigation row, completed controlled result, unchanged E1 and contiguous ordered trace events. Reopening the database preserves failure metadata, accepted evidence and the completed controlled result.

Actual captured failure metadata:

```json
{
  "category": "rate_limit",
  "http_status": 429,
  "provider_code": "rate_limit_exceeded",
  "request_id": "req_offline_123",
  "transient": true,
  "retry_after_seconds": 2.0,
  "retry_after_supplied": true,
  "stage": "provider_sdk",
  "agent_step": 2,
  "provider_attempt": 2,
  "retry_scheduled": true,
  "retry_decision": "scheduled"
}
```

These identifiers and failures are synthetic test fixtures. They are not evidence of a new Groq request or a recovered live investigation.

## Tests and actual results

| Validation | Actual result |
|---|---|
| Pre-fix failure reproduction | Two tests exposed the missing envelope: one failure, one error; retained separately |
| Boundary tests after initial fix | 2/2 passed |
| Focused reliability suite before final additions | 20/20 passed in 14.147s |
| Full final suite | **108 tests in 132.152s — OK, exit 0; no failures/errors/skips** |
| Previous 85 tests | All included and passing |
| Real HTTP transport guard | Enabled; **0 blocked request attempts** |
| SDK behavior | HTTPX MockTransport only; a real SDK-generated rate-limit exception crosses the worker boundary, with no hidden SDK retries |
| Windows process boundary | Real spawn worker preserves sanitized metadata |
| Retry/no-retry behavior | Temporary 429 and service errors; run-wide retry cap; attempt/time budget; Retry-After seconds/date/invalid/long values; permanent/no-retry cases |
| Evidence and persistence | Accepted evidence unchanged after retry, no duplicate analytical execution/output, failed-call deduplication, reopened SQLite retains metadata/results |
| Invalid outputs | Malformed calls, invalid JSON, empty SDK choices, invalid arguments and unsupported final citations classified separately |
| Sensitive data | Synthetic secret/body/prompt sentinels absent from failure records/checkpoints; assembled prompt absent from new checkpoint and database |
| Compilation / dependency consistency | Changed Python modules compiled; `pip check`: no broken requirements |

Full result files: `evidence/phase4c-reliability/full-tests.txt` and `full-tests-exit.txt`. Some existing tests intentionally emit application error logs while testing failure handling; the unittest result is nevertheless 108 passing tests.

A preliminary focused run encountered the restricted Windows temporary-directory permissions and a spawn-fixture startup timeout. The rerun used the existing workspace temporary directory and a lightweight spawn-importable fixture with the production-sized 30-second ceiling. Preliminary logs were preserved rather than overwritten. These execution-environment issues were resolved before the final full run.

### Reproduction command — offline

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
$env:TEMP = Join-Path (Get-Location) '.runtime/migration-temp'
$env:TMP = $env:TEMP
.\.venv-migration\Scripts\python.exe scripts/run_offline_regressions.py
```

The helper uses all tests under `tests/`, blocks real synchronous/asynchronous HTTP transports and Requests calls, and uses offline cached model settings. ASGI test clients and HTTPX MockTransport remain usable. Spawned agent fixtures use controlled providers/local analytical tools only. No provider credentials are needed.

## Preservation and limits

Changed existing application files are limited to:

- `lifelinetwin_backend/agent.py` — classified failure events, one run-wide retry, attempt accounting, evidence reuse and prompt-free checkpoint persistence.
- `lifelinetwin_backend/agent_limits.py` — safe typed error envelope across Windows subprocess boundaries.
- `lifelinetwin_backend/agent_provider.py` — invalid SDK response classification and safe response request ID.

Added `agent_failures.py`, 23 reliability tests plus the lightweight fixture, and the offline regression helper. The Phase 4B documentation now describes the retry/privacy policy. No dependencies, AI models, database columns or tables were added. Geographic/forecast engines, original tests, cached data, original Phase 4A behavior and historical Phase 4C evidence remain unchanged. Preservation evidence is in `evidence/phase4c-reliability/preservation-after.json`.

This fix makes future failures diagnosable and allows one conservative transient retry. It cannot recover metadata discarded from the historical failed run, guarantee provider service availability, or establish a completed live end-to-end investigation. None was attempted here. No provider/model change, live provider request, Docker/WSL/Zetaris installation, Meterless change, frontend, commit or push was performed.

Stopped after local reliability validation and reporting.
