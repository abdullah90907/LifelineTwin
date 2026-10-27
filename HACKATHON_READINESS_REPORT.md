# LifelineTwin — Hackathon and Zetaris Challenge Readiness

**27 October update:** the expanded official event rules, section 5.1, require
both Zetaris and Meterless for **every submission**, including Track 02.
Any narrower interpretation in this earlier assessment is superseded by
[HACKATHON_FINAL_READINESS.md](HACKATHON_FINAL_READINESS.md).

Assessment date: 27 October 2026, Asia/Karachi. This is a project and submission
assessment, not a claim of contest eligibility or a completed sponsor integration.

## Overall finding

The existing project has a substantial working analytical core. Keep the current
geographic engine, forecasting model, FastAPI/SQLite backend and map workspace.
The major remaining work is live sponsor integration, hosted-agent completion,
reproducible distribution and submission evidence. No project rebuild is needed.

Zetaris has not been integrated: no successful real Zetaris SQL execution is
recorded. Meterless has separate reference checks, but is not the application's
current durable memory layer. Work with Space XAI coding agents is not established
by the repository evidence. Codex work should not be relabeled as that activity.

## Dates and competition distinction

The [current main event page](https://hackathon.genai.works/event/open-agent-hackathon-2026)
lists 27 October 2026, 23:59 UTC for submission closure. The supplied announcement
and other organizer material say 23:45 UTC. Plan to submit by the earlier time:
**04:45 PKT on 28 October**; 23:59 UTC is 04:59 PKT.

The separate Zetaris Demo Challenge announcement supplied by the user says
29 October–5 November, ending 23:45 UTC. If these dates refer to 2026, its close
is **04:45 PKT on 6 November**. Its
[official rules URL](https://www.zetaris.com/zetaris-demo-challenge-official-rules)
could not be retrieved with the web tool, so the challenge dates, full eligibility,
video-length limits and legal requirements have not been independently confirmed.
Do not conflate its judging with the main hackathon's judging.

The public event describes a track centered on explainable, evidence-backed
investigations, which fits LifelineTwin. It explicitly requires both Zetaris and
Meterless in the Wildcard track. Detailed requirements for the selected track
still need checking in the organizer's rules/submission portal.

## What works and what the evidence actually establishes

| Area | Current achievement | Remaining qualification |
|---|---|---|
| Geography | Genuine Heidelberg OSM graph, 1,060 nodes / 2,331 directed edges; baseline access, hypothetical closures, individual/pair restorations | Distance-only, snapped-node and facility-capability limitations remain |
| Environment | Cached Open-Meteo estimates and existing local IBM Granite TTM pretrained inference | Historical replay, not current conditions; weather does not establish road closures |
| Backend | FastAPI, typed schemas, incidents, evidence, recommendations, SQLite and restart persistence | Clean installation from a distributed repository is not verified |
| Agent | LangGraph tool selection, durable trace, bounded attempts/retry and source citations | Six genuine hosted responses/tool calls were demonstrated, but the last live run did not submit a final result |
| Reliability | Phase 4E recorded 130 passing Python regressions and calibrated local input admission | Those tests are historical/offline, not a new successful hosted investigation |
| Frontend | MapLibre analytical workspace, origin/route inspection, real hypothetical comparisons/restoration previews, on-demand local forecast chart and record browsing | Redesign final report, complete responsive acceptance and clean-setup testing were interrupted and remain to finish |
| Zetaris | Setup research, proposed SQL and documented official client path | No platform installation, working endpoint, integration adapter or live query evidence |
| Meterless | Separate upstream smoke/conformance/idempotency and road-reference checks | Additional reopen test failed; no demonstrated integration into the current app workflow |
| Space XAI | No matching implementation/provenance found in inspected application/docs | Demonstrate actual qualifying development work if claiming this criterion |
| Submission | Phase reports and technical evidence exist | No local commits or Git remote; no demo video found in the project scan; submission link not verified |

Today the complete frontend test suite passed **25 tests in 3 files**. A fresh
production check found an unsupported MapLibre `retainPadding` option. Only that
option was removed, then TypeScript and the Vite production build passed, exit 0.
The geospatial renderer's large split chunk produces a build warning, not a build
failure. No backend analytical code was changed for this assessment.

Evidence: `evidence/challenge-readiness-20261027/frontend-tests.txt`,
`frontend-build.txt` (initial failure), `frontend-build-final.txt`, and
`frontend-build-final-exit.txt` (0). The earlier `frontend-exits.json` deliberately
retains the initial build failure and must not be mistaken for the final outcome.

## Zetaris installation/access blockers checked today

- `wsl --status`: exit 50, explicitly reports WSL is not installed.
- Docker CLI not found; neither inspected standard all-user nor per-user Docker
  Desktop executable path exists.
- Usable physical memory: **15.67 GiB**; available memory during the check:
  **1.38 GiB**. Availability varies with running applications.
- Prior hardware inventory reports four physical cores/eight logical processors;
  no allocation to a working Docker daemon has been verified.

The [official local prerequisites](https://github.com/zetaris/getting-started/blob/main/docs/install/choose-install.md)
recommend 8 GB available to Docker and four CPUs, with 15 GB free disk; preflight
rejects less than 6 GB. Windows uses Docker Desktop with WSL2. Close heavy
applications and remeasure before deciding whether this laptop can support a
stable concurrent demo. Initial WSL installation needs Windows administrator
access and may require restart. Sponsor distribution/access is another prerequisite.

An already authorized, adequately provisioned sponsor instance is an alternative
if offered. No such endpoint is currently confirmed. No AWS, paid service,
installation, administrator action, restart or account creation was performed.

## Recommended integration: one complete evidence workflow

Proposed architecture:

```text
Cached real assets + weather estimates + computed scenario outputs
                  -> supported data source(s) / Zetaris views
                  -> bounded backend Zetaris evidence adapter
                  -> deterministic or agent investigation + map evidence panel
```

1. Obtain working access and execute a real smoke query on Zetaris. This proves
   connectivity only, not meaningful application integration.
2. Prepare a small, reproducible read model with actual facility/OSM identifiers,
   timestamped weather estimates, separately classified TTM predictions, scenario
   accessibility and restoration outputs. Keep incidents/history in SQLite.
   Use connectors supported by the actual instance; do not assume a SQLite
   connector or invent SQL ingestion functions.
3. Add a backend-only adapter using Zetaris's
   [documented HTTP/client helpers](https://github.com/zetaris/getting-started/blob/main/scripts/HOWTO.md).
   Use bounded read-only query templates and a least-privilege account; keep
   credentials in server environment/private configuration. Record real request
   provenance, source names and sanitized failures.
4. Answer a useful question through Zetaris, such as joining affected sampled
   origins, facility records and scenario outcomes for a requested study/time
   context. Routing and TTM inference remain in their existing Python engines.
   Present weather as context, never as proof that a modeled closure is real.
5. Feed that actual query result into an evidence-backed backend/agent tool and
   show its provenance in the frontend. If unavailable, show an explicit local-only
   state rather than presenting a fallback as successful Zetaris execution.
6. Validate the returned numbers against the deterministic engine, test failures
   and persistence, and capture the entire real request/result-to-product flow.

This is a moderate extension to data access and evidence presentation, with
substantial environment/verification work. A planning allowance of roughly
**2–5 focused development days after access works** is reasonable for a narrow,
tested vertical slice plus packaging; this is not a delivery guarantee. Account
access, installation, runtime resources and provider reliability can extend it.

## Other priorities before claiming submission readiness

- Run one separately authorized, bounded hosted investigation after calibration.
  Verify accepted final findings, exact evidence and restart retrieval. Controlled
  providers and successful individual tool calls are not a substitute.
- For the main hackathon, determine the selected track's exact sponsor conditions.
  If Meterless is required, integrate a real useful engine role and fix/avoid the
  known persistence limitation before claiming durable memory. The organizer's
  [course overview](https://academy.genai.works/courses/open-agent-hackathon-2026/details)
  also discusses Nightshift/Nemotron; learning material alone does not establish
  that every sponsor product is mandatory for every category.
- Preserve genuine Space XAI development evidence if claiming its announced
  15-point demo criterion. Do not switch runtime models merely to manufacture a
  coding-tool claim, or describe unperformed work as completed.
- Rewrite the README's current-status section: it still contains prominent
  obsolete statements about missing frontend/agent capabilities and old runtimes.
  Keep phase history in reports, make the current setup path unambiguous, explain
  cached data/model provisioning and distinguish live, offline and hypothetical.
- Prepare a shareable repository only with user authorization to commit/push.
  Review secrets, licenses/attribution and ignored runtime assets. Test a fresh
  setup rather than relying on this machine's populated virtual environment/cache.
- Finish the frontend redesign acceptance report and outstanding responsive QA.
  Prioritize reliable investigation/data flow over adding more interface modules.

## Demo Challenge packaging from the supplied announcement

These requirements are based on the user's announcement, not independent access
to the full challenge rules:

- Record Zetaris working live within LifelineTwin, not only a branded screenshot
  or a successful connection test. Meaningful use plus how it helped account for
  40 of the announced 100 judging points.
- Include a 40–60 second personal explanation of what surprised/helped the team;
  do not confuse that segment length with the total video's permitted length.
- Add the requested one-sentence explanation to the write-up, grounded in what
  the completed integration actually demonstrated.
- Name the file `TEAM-NAME_DDMMYY`, with the team/date confirmed for the entry.
- Check video access, README and repository links from a clean/logged-out context;
  review full rules and attribution consent before submitting.
- Upload only after the user approves the concrete submission. No Dropbox upload
  or entry submission was performed in this assessment.

LifelineTwin is a credible technical foundation, but a compliant live sponsor
demonstration and a reproducible submission are still outstanding. The next
milestone should be real Zetaris access followed by one useful end-to-end query
inside the investigation workflow.
