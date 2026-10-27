# Phase 4E — Agent Context Budget Calibration

Date: 2026-10-26. All verification in this phase is offline; no hosted LLM request was made.

## Decision and scope

Raised the default estimated-input admission ceiling from **3,500 to 4,200 (+20%)**, retaining the original conservative estimator and every existing tool/context strategy. A shared constant now supplies ContextPolicy, ProviderConfig and environment parsing, avoiding default drift between orchestration and SDK admission. Explicit operator environment settings take precedence.

This is local engineering headroom, not a discovered Groq quota. No provider/model change, runtime self-tuning, tokenizer dependency, training or analytical calculation change was introduced. The agent still chooses tools, ordering, batching, inspections and completion. No rigid workflow was introduced into production code.

## Measured calibration evidence

Source: the six actual Groq responses in `evidence/phase4c-final/live-aj_5_217/summary.json`, reviewed alongside AI_AGENT_FINAL_TEST_REPORT.md and Phase 4D implementation/report.

| Request | Estimated input | Provider input | Excess estimate |
|---:|---:|---:|---:|
| 1 | 2482 | 1351 | 1131 |
| 2 | 2919 | 1623 | 1296 |
| 3 | 3217 | 1855 | 1362 |
| 4 | 3324 | 1925 | 1399 |
| 5 | 3414 | 1941 | 1473 |
| 6 | 3429 | 1941 | 1488 |

All six inputs were overestimated by approximately **1.73–1.84 times**. These samples share one provider/model and a narrow English/JSON investigation workload. They do not establish tokenizer behavior for arbitrary text, Unicode, tool arguments or future model revisions. Consequently the estimator remains `ceil(serialized UTF-8 bytes / 3) + 128 + 16 * message_count`; it is still explicitly labeled an estimate. Raising admission modestly preserves this margin rather than fitting a smaller estimator to six observations or trusting arbitrary runtime usage to relax limits.

The rejected historical candidate had a 3,653 input estimate, 10,142 serialized bytes and no provider token count because it was never sent. The calibrated ceiling gives that candidate 547 estimated tokens of headroom. No claim is made that Groq would accept it or complete the investigation.

## Offline historical reconstruction

`scripts/calibrate_context_budget.py` reconstructs the redacted six tool exchanges with current source projections and evaluates both old and new policies, without retaining assembled prompts or accessing credentials. Numeric output: `evidence/phase4e/calibration.json`.

The old-policy reconstruction reproduces the decisive **3,653-token / 10,142-byte** rejection at step 7. With the new policy, all seven reconstructed request contexts fit. At step 7 the context manager can retain the richer newest complete exchange: **4,125 estimated input tokens, 11,510 bytes, 5,925 estimated input-plus-output reservation**. This demonstrates admission and useful context retention, not a seventh hosted response. Reconstructed JSON argument formatting differs slightly from original wire data; raw historical wire payloads were not saved. Historical evidence was read only, and no previous outcome was relabeled.

## Preserved protections

- Exact compact-serialization request ceiling remains **12,000 bytes**, independently enforced alongside the input estimate in orchestration and the SDK adapter.
- Output reservation remains **1,800** maximum tokens. Optional run-local rate accounting still reserves estimated input plus output, reconciles valid usage and retains reservations after unknown failures.
- Operator input/rate overrides, total deadline, per-call timeout, maximum provider attempts, maximum tool calls and one eligible transient retry per run are unchanged. HTTP 413 is not retried automatically.
- Full evidence, source classifications, exact RFC6901 citations, paged inspections, analytical-tool reuse, SQLite persistence and credential redaction remain intact. No assembled raw provider prompts are added to storage.
- A question or requested inspection that cannot fit still yields a visible local limit rather than silent removal or bypass. An explicit input override of 3500 still enforces the old ceiling; remove or deliberately update such an override to use the calibrated default.

## Tests and actual results

**Complete regression suite: 130 tests passed in 249.574 seconds, exit 0.**
This includes all 124 prior tests plus six new calibration tests, with no failures,
errors or skips. Runner telemetry reports **zero real HTTP attempts**, with real
HTTP transports blocked. Runtime: existing `.venv-migration`, Python 3.13.3 on
Windows. Full results: `evidence/phase4e/full-tests-final.txt`; exit status:
`evidence/phase4e/full-tests-final-exit.txt`.

Six new calibration tests cover measured estimator accuracy, historical rejection
replay, shared defaults/operator overrides, exact token/byte edges, Unicode byte
overflow, unchanged output/rate reservations with missing usage, and a realistic
eight-round controlled investigation through existing analytical services.

The new eight-round case repeats the six historical tool choices, then requests
two source inspections and submits a final evidence-bound selection. Follow-up
inspection and completion depend on actual returned evidence, not hardcoded
geographic outcomes. It uses cached Heidelberg routing, Open-Meteo estimates and
the existing local pretrained IBM TTM model. The test completed **8 model rounds,
9 tool calls**, with peak **11,021 bytes / 3,980 estimated input tokens**. The
repeated incident call reused its evidence ID. Final source values/citations and
human-review advisory recommendations were validated, and a fresh application
and SQLAlchemy engine retrieved an identical result and trace. No provider retry
occurred. This is controlled offline completion, not genuine hosted LLM evidence.

All previous real-tool geographic-first, weather-first and shared-scenario cases
remain in the complete suite, alongside malformed calls, transient/no-retry
paths, tool/iteration deadlines, local rejection, paging and evidence integrity.
Measured audit and test logs are in `evidence/phase4e/`.

Two initial sandboxed launches (a full run and a diagnostic focused run) stalled
at local TestClient startup before creating the temporary SQLite database. Both
were interrupted and are not counted as passing executions. The full guarded
suite was rerun outside the restricted Windows sandbox; tests then progressed.
This behavior implicates the sandbox's local event-loop/IPC restrictions, not
provider context admission; the exact OS-level restriction was not diagnosed.
No application workaround or network permission change was introduced in code.

## Reproduction

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
$env:TEMP = Join-Path (Get-Location) '.runtime/migration-temp'
$env:TMP = $env:TEMP
.\.venv-migration\Scripts\python.exe scripts/run_offline_regressions.py
.\.venv-migration\Scripts\python.exe scripts/calibrate_context_budget.py evidence/phase4e/calibration-new.json
```

The audit uses exclusive file creation so previous measurements are not overwritten. The regression runner forces cached HF execution and blocks real HTTP transports; controlled providers are explicitly labeled and are never presented as live LLM success.

## Remaining limits

Provider/account quota and true tokens for unsent contexts remain unknown. The fixed heuristic can still overestimate or underestimate unfamiliar content. Extra local headroom can admit larger requests and consume more tokens; the unchanged byte/output/time/attempt caps bound this, but do not guarantee account-wide rate safety. Optional rate limits must be supplied from actual account knowledge, and other clients' usage is outside this process's window.

The request minimum can still exceed a configured limit after enough evidence or detailed inspections. Such runs correctly stop with sanitized diagnostics. This phase does not demonstrate actual hosted-model reasoning quality, live completion, or resolution of every possible Groq rate failure. A future live test requires separate authorization; none was performed here.

No new models/dependencies, frontend, Docker/WSL/Zetaris/Meterless changes, commits or pushes were made. Geographic and forecasting engines and historical evidence were preserved. Stop after offline calibration and regression reporting.
