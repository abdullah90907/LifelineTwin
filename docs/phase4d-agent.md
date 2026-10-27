# Phase 4D: bounded context and evidence-driven investigations

The existing LangGraph loop, Phase 4A endpoints, SQLite evidence and analytical
engines remain. This phase changes how evidence reaches the model and how a
request is admitted, not which investigation sequence the model must follow.

## Context and retrieval

Every model call contains the original investigation question, a short incident
view, the system safety policy, all tool choices, an evidence catalog and the
latest complete exchange when it fits. Older exchanges become explicit
server-generated archive markers. They do not pretend to be generated reasoning.
Tool-call/result pairs stay protocol-valid; an orphan tool response is never sent.

Evidence summaries are deterministic projections of actual results:

- Geography: baseline distances, changed origins, hypothetical closure endpoints,
  individual/pair restoration metrics and original source pointers. Facility lists
  and route paths stay in full evidence rather than being repeated every turn.
- Weather: source/time coverage, variables/units, quality counts and recent values;
  forecasts remain separately labeled predictions with exact samples, timestamps,
  units and model identity.
- Incident/previous investigations: attributed claims and historical result
  references, with untrusted narrative detail available on demand.

The compact working catalog retains beneficial restoration references and key
forecast information even when the newest exchange needs a smaller view. A latest
inspection is never silently discarded to make a request fit. If minimum useful
context cannot fit, execution ends with an explicit local context-budget result
before calling the provider.

`inspect_evidence` keeps the same name and source-pointer semantics, adding optional
paging fields:

```json
{"evidence_id":"E3","pointer":"/observations/variables/temperature_2m/values","offset":32,"limit":4}
```

Arrays return bounded item pages with original pointers and `next_offset`. Large
objects expose key pages for drill-down; text supports `text_offset` and
`text_limit`. Full source data are not replaced by these previews. Final citations
must still use the original evidence ID and pointer, not a summary/page wrapper.
The final resolver continues to supply exact stored numerical values.

The model may batch independent calls, choose a different tool order, inspect
details, compare scenarios or stop with disclosed partial evidence. No fixed
geography-weather-forecast script was added. `analyze_closures` already includes
baseline, closure and restoration comparisons, so a separate baseline call is not
required. `compare_restorations` can reuse the same validated scenario evidence;
reversing closure-ID order does not cause recomputation.

## Provider admission and usage

Provider/model/key settings remain unchanged. Additional optional environment
settings, read when creating the real provider adapter:

| Variable | Default | Meaning |
|---|---:|---|
| `LIFELINETWIN_LLM_MAX_INPUT_TOKENS` | 4200 | Estimated input-token admission ceiling (Phase 4E calibration) |
| `LIFELINETWIN_LLM_MAX_REQUEST_BYTES` | 12000 | Serialized JSON request-byte ceiling |
| `LIFELINETWIN_LLM_MAX_OUTPUT_TOKENS` | 1800 | Output reservation, configurable 256–1800 |
| `LIFELINETWIN_LLM_TOKENS_PER_MINUTE` | Unset | Optional operator-supplied token-window budget |
| `LIFELINETWIN_LLM_MAX_RATE_WAIT_SECONDS` | 60 | Maximum local pacing wait, also bounded by run deadline |

These defaults are conservative engineering settings, **not discovered Groq
limits**. Tokenization is estimated from UTF-8 bytes plus framing, without
downloading a tokenizer/model. A byte count is exact for the serialized payload;
an estimated token count cannot guarantee the provider's count or account quota.
SDK-reported usage is retained numerically for comparison/calibration.

Phase 4E raises only the default input ceiling by 20%, retaining the original
`ceil(serialized_utf8_bytes / 3) + 128 + 16 * message_count` estimate. Six saved
Groq requests were overestimated by 1.73–1.84 times; that small sample does not
justify fitting a tokenizer or automatically learning looser limits at runtime.
The previously unsent 3,653-token estimate now fits. The 12,000-byte ceiling,
1,800-token maximum output reservation and operator overrides remain unchanged.
An explicit environment value of 3500 will still enforce 3500; remove that override
or deliberately update it to use the calibrated default. See PHASE4E_REPORT.md
for offline measurements and remaining quota uncertainty.

The orchestrator and SDK adapter both check request size before transmission.
The optional sliding window reserves estimated input plus maximum output, charges
reported usage after successful requests, and retains reservations after unknown
failures. It can pace requests within the configured wait/run budget, otherwise
stop locally with `rate_budget`. This is run-local accounting; it cannot account
for other applications using the provider account. No quota is silently guessed.

The Phase 4C reliability policy remains: one eligible transient retry per run,
SDK retries disabled, bounded attempts/time, no whole-investigation retry. HTTP
413 is still reported honestly and not automatically retried. Context metrics,
usage and admission decisions are stored without raw assembled prompts or keys.

## Reproduce offline

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
$env:TEMP = Join-Path (Get-Location) '.runtime/migration-temp'
$env:TMP = $env:TEMP
.\.venv-migration\Scripts\python.exe scripts/run_offline_regressions.py
.\.venv-migration\Scripts\python.exe scripts/demo_phase4d_offline.py
.\.venv-migration\Scripts\python.exe scripts/benchmark_phase4d.py
```

The demo's provider is an explicitly controlled test fixture, using real cached
Heidelberg/TTM tools, follow-up inspections and SQLite retrieval after application
restart. It is not live LLM evidence. The benchmark replays recorded tool results
in memory and stores only measurements. It does not make provider requests or save
raw reconstructed messages. Choose a new output path when using `--output`;
benchmark files are created exclusively to preserve previous evidence.

## Another live verification

No live Groq call was made in Phase 4D. Before a separately authorized attempt,
confirm current credentials privately and obtain the actual account/model limits
from the provider console. Set the optional window budget if known. Use the same
model/endpoint and `scripts/verify_phase4c.py --final`; it now records context and
usage measurements and accepts a scenario baseline computed inside closure
analysis rather than requiring a redundant standalone baseline call.

Completion, recommendation quality and quota compatibility with the actual hosted
model still require live verification. New diagnostics can distinguish local
admission failures from provider rejections without hiding either.
