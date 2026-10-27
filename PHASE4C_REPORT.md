# Phase 4C — Live LLM Agent Verification

Date: 2026-10-25 (Asia/Karachi). Repository: `D:\Projects 2026\LIfelineTwin`.

**Outcome: PARTIALLY VERIFIED; end-to-end success criteria NOT MET.** A genuine Groq-hosted model selected and successfully executed three real LifelineTwin tools through LangGraph. The investigation then failed on a subsequent provider invocation and produced no accepted final findings or recommendations. The failed run and ordered trace survived a real backend process restart identically. A targeted SDK diagnostic from the same checkpoint subsequently succeeded. At the user's explicit instruction, no additional investigation or live request was made after that diagnostic.

**Regression result: all 85 tests passed**, including all Phase 4A/4B tests. No fake model was used as evidence of live functionality.

## Provider and configuration

| Setting | Actual value / handling |
|---|---|
| Provider | Groq |
| Configured endpoint | `https://api.groq.com/openai/v1` |
| Configured and returned model | `openai/gpt-oss-20b` |
| Token parameter | `max_tokens` |
| SDK | Existing standard OpenAI Python SDK through the existing Phase 4B adapter |
| Credential | Supplied transiently using hidden input; set only in the verification process environment and inherited by its own backend workers. Not written to configuration, source, logs, SQLite or reports. |

Initial inspection found the four provider variables absent from the process, Windows User/Machine environment, and local configuration. The user supplied the exact non-secret model/endpoint/token settings. No model was substituted. The credential was not requested again or displayed. The verification used environment-based provider configuration without changing permanent Windows environment settings.

Official Groq compatibility and tool-use documentation was retrieved successfully (HTTP 200). The browser/search connector was unavailable, so documentation was read directly through the existing HTTP client. Evidence: `evidence/phase4c/official-doc-check.json`.

## API availability and compatibility checks

1. **Initial forced toy-function probe:** Groq returned HTTP 400, error code `tool_use_failed`, message `Failed to parse tool call arguments as JSON`. This was a synthetic API compatibility probe, not an incident investigation; no analytical tool executed. Redacted evidence: `evidence/phase4c/live-0y88wvmx/summary.json`.
2. **Ordinary minimal completion:** succeeded with the exact configured model. Returned model: `openai/gpt-oss-20b`; finish reason `stop`; usage 75 prompt + 43 completion tokens, total 118. This establishes credential/API/model availability, not tool-calling reliability by itself. Request ID: `req_01m5sy0qweeke93w8hk02w8bwv`. Evidence: `evidence/phase4c/live-q4pmoaf9/minimal-probe.json`.
3. **One bounded live investigation:** executed via the existing agent HTTP endpoint using production `tool_choice=auto`. Three real model responses and three successful tools were recorded, followed by a provider-level failure. Details below.
4. **One targeted checkpoint diagnostic:** repeated the pending SDK request from the saved checkpoint with no new incident or analytical execution. It succeeded, returned model `openai/gpt-oss-20b`, finish reason `tool_calls`, and selected `generate_forecast`. Usage: 5,485 prompt + 231 completion tokens, total 5,716. **That diagnostic tool selection was not executed and is not counted as a successful agent forecast call.** Evidence: `evidence/phase4c/live-gcrpsfad/summary.json`.

The failure on the production path did not reproduce in the targeted diagnostic. The existing Phase 4B worker boundary deliberately strips external exception messages, so the original failed invocation's HTTP/error classification was not retained. It is therefore not established whether that failure was a transient parser, transport, service-limit or other provider issue. No speculative provider-adapter change was made. In particular, the diagnostic's success is not proof the failed investigation recovered.

All SDK calls used retries disabled. No provider/model exploration, repeated investigation loop, or additional live calls followed the user's stop instruction. One incident investigation was attempted; the probes and one diagnostic above were separate bounded checks. The exact billable request count cannot be inferred from the failed worker alone; three successful investigation model responses are auditable.

## Actual live Heidelberg investigation

Evidence directory: `evidence/phase4c/live-q4pmoaf9/`.

- Incident ID: `0362174c-02f5-4160-b22a-bfeb4db429d3`.
- Agent run ID: `29abf9b4-6244-4b24-a8cf-55d75c900c92`.
- Scenario: explicitly hypothetical, using three approved segments derived from existing cached Heidelberg betweenness analysis, excluding the Phase 2-selected pairs. No real road incident was asserted.
- Limits: 8 LLM rounds, 16 tool calls, 240 seconds total, 60 seconds per analytical call; existing 30-second per-provider-call cap and 1,800-token output cap retained.
- Final status: **failed**, 3 accepted model-response rounds, 3 successful tools, no accepted result.
- A Phase 4A deterministic investigation of the same scenario also completed in the fresh verification database, enabling numerical cross-checks without additional hosted LLM requests.

### Ordered agent trace

| Sequence | Recorded event | Actual outcome |
|---:|---|---|
| 1 | Run start | Configured real SDK provider identity, no fake provider |
| 2 | Model decision | `openai/gpt-oss-20b` selected `retrieve_incident` |
| 3 | Tool execution | Incident details returned successfully, evidence `E1` |
| 4 | Model decision | Same actual model selected `baseline_accessibility` |
| 5 | Tool execution | Cached real geographic analysis returned successfully, evidence `E2` |
| 6 | Model decision | Same actual model selected `retrieve_observations` |
| 7 | Tool execution | Real cached Open-Meteo environmental estimates returned successfully, evidence `E3` |
| 8 | Run end | `Provider failed or returned an invalid tool-call response; no LLM findings were accepted` |

The initial incident snapshot is also retained as `E0`. Sequence numbers are contiguous. Selected tools came from real provider responses, not a script or fake response sequence. Full redacted inputs/outputs and bounded untrusted assistant notes are in `agent-trace-redacted.json`. No hidden chain-of-thought is requested or presented as evidence.

The LLM did **not** execute `generate_forecast`, closure/restoration comparison, or `complete_investigation` within this run. It is incorrect to describe this as a completed investigation or to claim that it generated final evidence-backed recommendations.

## Evidence-grounding checks

Offline verification of the actual persisted data found:

- The live agent's baseline route records exactly equal the Phase 4A deterministic baseline for the same dataset/origins/facilities.
- The live agent's returned observation values exactly equal the Phase 4A environmental observation values.
- Environmental source: `https://api.open-meteo.com/v1/forecast`, from the existing historical snapshot. These are model-derived recent-past estimates, not verified station measurements or proof of a road closure.
- Eligible source context: 740 past hourly records, with 148 future source hours excluded by the existing adapter.
- Source snapshot SHA-256: `39c9e7f148c07179e4130a9c2cfd30c835b0352a5deadbaba01ba0eec4334250`.
- The existing joint environmental adapter computes/caches local TTM alongside observations. However, no separate forecast output was returned to the LLM in the failed run, and no forecast value was accepted as a final LLM finding. The successful Phase 4A prediction is not mislabeled as a live-agent forecast finding.
- No final findings or recommendations exist, so final citation fidelity and recommendation grounding could **not** be verified for this live run. Phase 4B's controlled tests of those contracts still pass, but they are not live-model evidence.

These checks are recorded in `evidence/phase4c/offline-verification.json`.

## OSM-endpoint comparison with Phase 4A

The deterministic result and direct graph recomputation agree on the following hypothetical pair reopenings. The live agent never reached closure/restoration analysis, so these measurements are **deterministic reference results, not live-agent numerical findings**.

| Reopened OSM endpoint pairs | Origin-metres saved versus the fully disrupted scenario |
|---|---:|
| `(33811019, 928125779)` and `(60697812, 146000024)` | 432.8682130453435 |
| `(33811019, 928125779)` and `(60697818, 298538536)` | 0.0 |
| `(60697812, 146000024)` and `(60697818, 298538536)` | 0.0 |

The helper reconstructs the graph with each remaining closure and calls the original accessibility engine. No D1/D2/D3 label is treated as independent road identity. All three pair savings match the completed Phase 4A result. There is no evidence that the incomplete live investigation is better than the deterministic workflow.

## Restart and audit persistence

The verification stopped only its own localhost backend process, started a new process against the same SQLite file, and retrieved the saved run and ordered trace.

- Saved **failed run** identical after restart: true.
- Saved ordered trace identical after restart: true.
- SQLite `PRAGMA integrity_check`: `ok`.
- Accepted completed investigation after restart: **not demonstrated**, because the live run never completed.

Artifacts retained under `live-q4pmoaf9/` include `verification.sqlite3`, `requests.json`, `minimal-probe.json`, `agent-result-redacted.json`, `agent-trace-redacted.json`, `http-transcript-redacted.json`, `deterministic-result.json` and `summary.json`. The failed toy probe and successful checkpoint diagnostic remain in separate directories.

## Regression tests and preservation

Command:

```powershell
$env:HF_HOME = Join-Path (Get-Location) '.runtime/huggingface'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
.\.venv-migration\Scripts\python.exe -m unittest discover -s tests -v
```

Actual result: **Ran 85 tests in 114.305s — OK, exit 0, no failures/errors/skips**. Evidence: `evidence/phase4c/regression-tests.txt` and `regression-tests-exit.txt`. The regression suite's controlled fake providers remain test-only and are not evidence of live success. `pip check` reports no broken requirements.

SHA-256 preservation check: all 45 pre-existing backend, analytical, test and cached-data files are unchanged. No provider-adapter, LangGraph, Phase 4A or Phase 4B application code was modified. A new `scripts/verify_phase4c.py` helper performs bounded live verification, hidden credential intake, redacted evidence capture, direct analytical checks and restart verification. No dependencies or models were installed.

The helper's plaintext-stdin mode could not receive input from a closed command pipe and exited before making any API call. Hidden terminal input was used instead. The credential was not placed in command arguments or stored on disk. Scans of saved verification artifacts found no credential or provider-key prefix. No permanent environment or configuration file was created.

## Reproduction and limits

Use the same existing provider environment variables, with a private credential configured in the process environment. Do not put the key in a command line, incident, question, report or source file.

Non-secret settings used:

```powershell
$env:LIFELINETWIN_LLM_MODEL = 'openai/gpt-oss-20b'
$env:LIFELINETWIN_LLM_BASE_URL = 'https://api.groq.com/openai/v1'
$env:LIFELINETWIN_LLM_TOKEN_PARAMETER = 'max_tokens'
```

After privately setting the API-key environment variable, the opt-in verification command is:

```powershell
.\.venv-migration\Scripts\python.exe scripts/verify_phase4c.py
```

It attempts one small completion and one bounded incident investigation and creates fresh evidence. A hidden interactive credential option is available through `--stdin-key`. Neither command was run again after the user instructed stopping. Retrying is not required to read any stored result or trace.

The success criterion remains outstanding: a genuine model must still complete all relevant tool work, submit validated findings/recommendations and retain that **completed** result after restart. This run proves genuine model availability, real LangGraph-selected tools, baseline/observation grounding and failed-run audit persistence; it does not prove full end-to-end completion or final recommendation quality. The provider failure's exact cause remains unknown. Further provider requests or compatibility work were stopped as instructed.

No fake model was used in live verification. No frontend, Docker, WSL, Zetaris, Meterless modification, additional LLM installation/training, commit or push was performed. Verification servers were stopped.

## Official resources consulted

- [Groq OpenAI compatibility](https://console.groq.com/docs/openai).
- [Groq tool-use overview](https://console.groq.com/docs/tool-use/overview).
