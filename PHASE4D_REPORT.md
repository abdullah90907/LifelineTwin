# Phase 4D — Intelligent Agent Reliability and Optimization

Completed: 2026-10-25 (Asia/Karachi). Repository: `D:\Projects 2026\LIfelineTwin`.

**Outcome:** Improved flexible LangGraph investigation implementation, validated entirely offline. **124 tests passed**, including all previous 108 tests. Three realistic controlled-provider investigations used genuine cached Heidelberg/weather/TTM tools, completed with exact source citations and advisory recommendations, and retained identical results/traces after application restart. **No live Groq API request was made.** Hosted-model completion remains unverified.

## Diagnosis: confirmed evidence versus hypotheses

Reviewed the Phase 4C and final verification reports, reliability report, redacted live traces, message construction, SDK adapter, tools, source storage, checkpoint/retry handling and configuration. The final historical run remains failed with HTTP 413, code `rate_limit_exceeded`, agent step 4 and a 36-second Retry-After. It was not rerun or relabeled.

### Confirmed architectural issues

An offline reconstruction of the recorded first three tool outputs found:

| Before provider call | Reconstructed original request bytes |
|---:|---:|
| 1 | 7,932 |
| 2 | 8,940 |
| 3 | 16,742 |
| 4 | 31,696 |

This reconstruction uses recorded inputs/outputs and null assistant notes; it is not the exact original wire request or a provider token count. Initial measurements are retained in `evidence/phase4d/diagnosis-before.json`.

Confirmed issues:

- Every previous tool response was appended indefinitely within the bounded run; a per-response 18,000-character cap did not bound the next complete provider request.
- Baseline and scenario responses repeatedly exposed routes, facility details and other data that were not necessary for every reasoning step. In the failing sequence, the baseline generic preview was about 6.7 KB and closure preview about 13.2 KB, both below the old per-tool cap and therefore both resent.
- Tool schemas and system policy were resent alongside growing messages. Original schemas occupied about 4.7 KB and the system policy about 1.6 KB in the initial measurement.
- There was no pre-transmission whole-request byte/input-budget admission, provider usage accounting or optional rate-window accounting.
- `analyze_closures` and `compare_restorations` performed the same complete geographic computation but had separate cache identities.
- Broad evidence inspection could fail on size or generic truncation instead of offering useful bounded pages and original source pointers.
- The final verification helper required a separate baseline tool call even when scenario analysis already contained the same baseline, unnecessarily constraining a valid agent plan.

### Not conclusively established

The exact Groq account/model quota, effective tokenizer count, request-size threshold and interaction with the token-per-minute window are unknown. Raw provider error bodies were intentionally not retained. A per-request token allowance and a rolling/shared quota remain plausible contributors; the available evidence cannot distinguish them conclusively. There is no basis for assigning the final run's classified error to an earlier unclassified failure, or for claiming that shorter output alone guarantees hosted success.

No evidence suggested that the routing/TTM engines produced incorrect calculations. Direct checks below preserve their results.

## Architectural decisions

The solution retains the existing model-controlled LangGraph loop and all nine callable tools. It introduces deterministic context management and evidence retrieval, not another LLM, a summarization model, a fixed investigation sequence or a fallback fake provider.

1. **Separate durable evidence from provider context.** Full validated tool outputs stay in SQLite evidence and ordered traces. Model-facing views are deterministic semantic projections with exact source measurements and original pointers.
2. **Use bounded working context.** Rebuild each provider input from the original question, short incident view, safety policy, evidence catalog and the newest complete exchange when it fits. Older exchanges become explicit server-generated archive markers, not fabricated reasoning. Tool-call/result pairs remain protocol-valid.
3. **Make detail retrieval useful.** Inspect original arrays through pages, large dictionaries through key pages, and long text through bounded windows. Final findings still resolve directly to original stored values, not summaries.
4. **Check the whole request and usage.** Apply admission before calling the SDK, retain byte/token-estimate and usage telemetry, and support an operator-specified run-local token window. Do not guess a real Groq quota.
5. **Reuse equivalent analysis.** Share cache identity for the two geographic scenario tools and normalized closure subsets, without forcing which tool the model selects.
6. **Keep recovery bounded and explicit.** Existing time/tool/attempt limits, one run-wide transient retry, no whole-run replay, privacy protections and honest provider-error records remain.

## Implemented changes

### Semantic evidence and context

New `lifelinetwin_backend/agent_context.py` provides:

- Geographic views with baseline distances, changed origins, hypothetical OSM closure endpoints, individual/pair savings and source pointers. Full paths and facility lists remain available without being repeated every turn.
- Observation views with source/time coverage, units, quality counts and recent values. They remain explicitly model-derived weather estimates.
- Prediction views with the existing TTM identity/revision, horizon, units and exact samples/extrema with timestamps and original value pointers.
- Compact incident/historical-result views, with untrusted narrative details available on demand.
- An evidence catalog preserving changed-origin references, beneficial restoration alternatives and key forecast information.
- Protocol-valid compaction strategies: retain the newest exchange, shrink its view when necessary, or use a lean catalog. A minimum context that cannot fit produces a visible local `context_budget` result rather than a provider request.

The original investigation question is not silently truncated. Full evidence is not modified. A requested inspection result is not silently archived away to make the next request fit. Source narrative remains untrusted; original source classification, human review and no-weather-implied-closure rules remain enforced.

Schema metadata redundant to validation was removed from model-facing JSON schemas, and descriptions/system wording were made more concise. All tool choices and server-side Pydantic validation remain. Independent tool calls may be batched at the model's discretion. The production code does not prescribe a geography-first or weather-first sequence.

### Retrieval and computation reuse

`inspect_evidence` preserves its original ID/pointer interface, with optional `offset`, `limit`, `text_offset` and `text_limit`:

- Array pages include original item pointers and continuation offsets.
- Oversized items expose structural descriptors for further drill-down.
- Large dictionaries expose key pages.
- Text windows preserve their source pointer and character offsets.

Final Citation input remains unchanged and refers to original source paths. No measurement is substituted by an LLM or by a truncated string. Source values remain available through the existing evidence/trace system.

The scenario tools share a semantic cache key. A later request through the other tool, including reversed closure-ID order, reuses the same evidence ID and does not repeat the geographic calculation or duplicate its full output. The trace still records the model's requested tool and reuse flag.

### Request and provider budgets

Optional environment settings added to the existing provider configuration:

| Setting | Default | Purpose |
|---|---:|---|
| `LIFELINETWIN_LLM_MAX_INPUT_TOKENS` | 3500 | Estimated input-token admission ceiling |
| `LIFELINETWIN_LLM_MAX_REQUEST_BYTES` | 12000 | Serialized JSON byte ceiling |
| `LIFELINETWIN_LLM_MAX_OUTPUT_TOKENS` | 1800 | Output reservation, bounded to 256–1800 |
| `LIFELINETWIN_LLM_TOKENS_PER_MINUTE` | Unset | Operator-supplied token-window budget, only if known |
| `LIFELINETWIN_LLM_MAX_RATE_WAIT_SECONDS` | 60 | Maximum local pacing wait, also limited by remaining run time |

These are engineering defaults, not discovered Groq limits. Token counts use a labeled UTF-8-byte/framing estimate without downloading a tokenizer/model. JSON bytes are measured exactly for the serialized payload. The orchestrator and SDK adapter both enforce admission. SDK-reported numeric usage is captured when available, including the difference from the input estimate for later calibration.

The optional sliding window reserves estimated input plus maximum output, reconciles successful calls using reported usage, and retains reservations after unknown failures. It may wait within the configured window/run budget; otherwise execution stops locally as `rate_budget`. This is run-local accounting, not an account-wide quota service. Other applications' usage and provider-specific counting can still cause a rejection.

Provider failures are not hidden. HTTP 413 remains non-retryable, and no automatic oversized-request regeneration was introduced. Retry and SDK attempt budgets remain bounded. Context/usage metrics store counts and decisions, not raw assembled prompts or credentials. No model/provider switch, new credential store or SQL schema migration was introduced.

## Measured improvements

### Historical replay with static fields held equal

`evidence/phase4d/context-replay-final.json` compares old append-only/generic-preview handling against managed handling for the same recorded tool choices and outputs. The current compact schemas/system and compact serializer are held equal on both sides to isolate dynamic context handling.

| Before call | Append-only bytes | Managed bytes | Managed input-token estimate |
|---:|---:|---:|---:|
| 1 | 6,543 | 6,918 | 2,482 |
| 2 | 7,531 | 8,131 | 2,919 |
| 3 | 15,313 | 9,305 | 3,326 |
| 4 | 30,247 | 9,381 | 3,367 |

At the previously failing fourth step, managed serialization is **68.99% smaller**. The catalog adds overhead to very short conversations; the first two requests are slightly larger, which is reported rather than hidden. Both source data and tool choices are identical in the comparison. Provider request count in this replay is unchanged; it is not a live latency, token-billing or reasoning-quality measurement.

Across the implementation, schema bytes decreased from the initial measured 4,727 to 4,017; system policy bytes from 1,562 to 1,141. These static reductions are separate from the equal-static replay comparison above.

### Real analytical tools, controlled provider investigations

Retained evidence directory: `evidence/phase4d/controlled-nonajmmb/`.

| Controlled case | Status | Model rounds | Tool calls | Peak request bytes | Peak input estimate | Reused tool calls |
|---|---|---:|---:|---:|---:|---:|
| Geographic-first | completed | 3 | 6 | 9,203 | 3,308 | 0 |
| Weather-first | completed | 4 | 6 | 9,641 | 3,438 | 0 |
| Shared geographic scenario | completed | 3 | 7 | 9,235 | 3,319 | 1 |

The provider here is a clearly labeled **controlled offline fixture**, not a genuine LLM. Its decisions depend on the current evidence catalog and actual follow-up inspection results. It selects a beneficial restoration only when the computed catalog reports one, checks actual OSM endpoint details and a forecast value before finalizing, and uses different tool orders for different questions. This verifies flexible orchestration, not hosted model intelligence or semantic robustness.

The tools use genuine cached Heidelberg geography, original weather snapshots and existing local IBM TTM weights. Each case retains about **84.2 KB of complete source evidence**, while requests stay under the configured 3,500 estimated input-token ceiling. There is no new model or training. The overlapping scenario call reuses the original real geographic result, avoiding one redundant analysis while preserving its source identity.

For every case:

- Final findings include geographic impact/restoration data, an actual TTM prediction and timestamp, and actual environmental source values.
- Every final citation equals its original stored value.
- Recommendations retain human-review requirements and valid evidence references.
- A fresh backend application/SQLAlchemy engine reading the same SQLite file retrieves an identical result and trace. These are application/engine restart checks, not a claim of a new live-server process verification.
- An independent offline audit reruns the original geographic engine and compares baseline, disrupted and change records, then checks every restoration pair using actual OSM endpoint sets.

Endpoint results match the preserved deterministic engine: reopening `(33811019,928125779)` plus `(60697812,146000024)` saves 432.8682130453435 origin-metres; the other two pairs in this scenario save zero. No model-authored number is used. Full audit: `evidence/phase4d/independent-evidence-audit.json`.

## Actual tests and evidence

Final complete run: **124 tests in 178.501 seconds — OK, exit 0, no failures/errors/skips**. All previous 108 tests are included. The offline HTTP guard reports **zero real HTTP attempts**. Existing negative-path tests may emit expected application error logs; these are not unittest failures.

The 16 new optimization tests cover:

- Bounded context without changing source evidence or dropping the question.
- Atomic exchange archival and tool-call protocol validity.
- Rejection before SDK construction when context cannot fit.
- Exact byte measurement and explicitly labeled token estimates.
- Sliding-window reservation/reconciliation and local rate/context admission with no provider call.
- Numeric SDK usage capture and configurable output reservation.
- Paged arrays/text, escaped pointers, large-object/item drill-down and unchanged sources.
- No silent loss of a latest inspection.
- Complete schema/tool registration and environment validation.
- Three genuine cached-data investigations with controlled decisions, different orders, source-dependent inspections, exact final citations, shared scenario evidence and restart retrieval.

Focused final optimization suite: 16 tests passed in 42.875 seconds. Existing reliability smoke suite: 23 tests passed. Compilation and `pip check` passed. New tests use controlled providers/MockTransport only; no Groq model was contacted.

The initial realistic tests exposed two issues before the final passing run: a lean catalog could lose the beneficial restoration reference, and the weather-first final step could exceed the conservative context budget. Both were fixed by preserving decision-relevant catalog facts, retaining inspection exchanges and removing redundant schema/archive text. Defaults were not raised to conceal these failures. Initial logs remain separate from final results.

Key artifacts:

- `evidence/phase4d/diagnosis-before.json`
- `evidence/phase4d/context-replay-final.json`
- `evidence/phase4d/full-tests.txt` and `full-tests-exit.txt`
- `evidence/phase4d/controlled-nonajmmb/summary.json` and the three complete controlled result/trace/checkpoint JSON files
- `evidence/phase4d/independent-evidence-audit.json`
- `evidence/phase4d/preservation-after.json`

## Reproduction

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
$env:TEMP = Join-Path (Get-Location) '.runtime/migration-temp'
$env:TMP = $env:TEMP
.\.venv-migration\Scripts\python.exe scripts/run_offline_regressions.py
.\.venv-migration\Scripts\python.exe scripts/demo_phase4d_offline.py
.\.venv-migration\Scripts\python.exe scripts/benchmark_phase4d.py
```

The demo allocates fresh controlled-evidence directories. The benchmark creates measurements exclusively, without overwriting prior outputs or storing reconstructed raw provider messages. Full architecture, retrieval examples and budget configuration: `docs/phase4d-agent.md`.

## Preservation and live-readiness assessment

Existing Phase 4A endpoint schemas, database schema, geographic engine, weather/TTM engines, cached data and all original tests remain intact. Changes are confined to agent/context/provider contracts, the existing verification helper, supporting tests/utilities and documentation. Source-preservation checks found no changed geographic/forecast engine, cached data or historical final-verification evidence. No dependencies, unrelated models, infrastructure, frontend, commits or pushes were introduced.

The final verification helper now records context/usage measurements and does not require a redundant standalone baseline call when scenario analysis already contains that baseline. This preserves model freedom rather than fixing a sequence just to satisfy a test.

**Ready for another separately authorized live verification, with limitations:** offline meaningful completion and context reduction are demonstrated, but actual Groq completion, semantic tool selection quality and quota compatibility are not. Confirm the current provider/model account limits privately and set the optional token-window budget if known. The byte-based estimator can differ from provider tokenization; the run-local window does not include other clients' usage. A completed bounded investigation can still be partial or scientifically limited. Existing distance/snapshot/centroid/facility caveats and advisory-only actions remain.

No live Groq calls, paid infrastructure changes, Docker/WSL/Zetaris installation, model training, frontend work, commit or push occurred. The historical live failure remains failed. Stopped after Phase 4D implementation, offline validation and reporting.
