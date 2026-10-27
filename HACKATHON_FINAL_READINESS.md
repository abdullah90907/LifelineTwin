# LifelineTwin — final readiness for this milestone

27 October 2026. **Working local investigation demonstration; not yet a
sponsor-compliant main-event submission.** This report supersedes the earlier
assessment's incomplete interpretation of sponsor requirements.

## Delivered

The map's disruption lab now connects to a complete, persistent investigation:
an explicit hypothetical title/cutoff → exact selected OSM endpoints → existing
geographic and environmental tools → computed consequences and restorations →
cited advisory actions → saved evidence accessible through the incident library.
The evidence page includes precise origin nodes, inspectable paths, restoration
metrics, a forecast scrubber, model/source metadata, assumptions and limitations.
Recommendation citations open their corresponding evidence records.

Saving is explicit. A pending save blocks repeated clicks; an ambiguous failure
does not automatically repeat a POST or start another investigation. Users are
directed to existing history before trying again. This is a browser safeguard,
not a new server-wide idempotency protocol.

**Real Meterless integration:** the installed WorldModel reference engine now
resolves hypothetical closure assumptions against the best computed restoration
preview. It records field-level sources, superseded facts, remaining assumptions
and zero-event duplicate replays. SQLite retains the accepted projection alongside
the analytical result. This does not rely on the reference engine's known
disk-reopen defect. A fresh in-memory engine runs in a bounded 15-second Node
subprocess; missing/failed runtime is explicitly `unavailable` and preserves the
standalone analytical workflow. No upstream vendor or analytical engine was changed.
The recommendation layer now selects the strongest computed alternative by
reconnection and distance saving instead of assuming the first row is strongest.

## Actual demonstration evidence

The browser created completed investigation
`3fa27737-ee0f-4ce4-ac55-b1e7015b3fbe` in the isolated database
`evidence/challenge-readiness-20261027/workflow.sqlite3`.

- Cached Heidelberg graph: 1,060 nodes, 2,331 directed edges, nine origins.
- Hypothetical segments: D1 `33811019 → 928125779`; D2 `60697812 → 146000024`;
  D3 `60697818 → 298538536`.
- O6, node `267161325`: 749.478014132016 m → 1,515.3044450550988 m;
  increase 765.8264309230827 m. All nine origins remain reachable.
- Individual reopenings save zero; D1 + D2 saves 432.8682130453435
  origin-metres, with no newly reconnected origins. This is not a repair cost or response time.
- Existing cached Open-Meteo estimates plus real local
  `ibm-granite/granite-timeseries-ttm-r1` inference, revision
  `f04bebdd4c13475b006ce72672e74c9dc28871dc`: 96 hourly predictions,
  148 future hours excluded at cutoff `2026-10-24T19:55:49Z`.
- Real Meterless supersedes D1/D2 assumptions for the restoration preview and
  leaves D3 assumed closed. These are scenario states, not real road observations.

Read-only verification compared **all** saved baseline, disrupted and reopening
paths with direct calls to the existing geographic engine and independently
summed restoration savings. All recommendation references resolve. After an
actual backend process restart, the complete saved JSON was identical:
canonical SHA-256 `ad3bbdb2af3dc3de33ee9aa2949e4597228f14ccb246db43856bbb18e05606a1`.
Before/after JSON, verification outputs, SQLite and desktop/mobile screenshots
are under `evidence/challenge-readiness-20261027/`. Existing application records
and earlier evidence were preserved.

The verification app is running at http://127.0.0.1:5175 with its isolated API
on port 8002. Normal startup instructions use ports 5173/8000 and the original
application database; the evidence database is separate.

## Verification

- Frontend: **29 tests passed**, TypeScript checks and Vite production build passed.
  MapLibre remains a large lazy-loaded chunk; Vite reports its bundle-size warning.
- Browser: actual map analysis → saved investigation → library/history → evidence
  citation checked. The evidence view has no page overflow at 1440 px or 390 px.
- Backend: **134 tests passed in 324.475 seconds**, with real HTTP transports
  blocked (one attempted request blocked; none transmitted). The first run had
  130 passes and four errors: legacy forecast tests selected a
  72-hour cache through date/mtime fallback. Those tests now explicitly use the
  existing 888-hour research snapshot, without changing weather/forecast engines.
  The failed run is retained in `python-tests-workflow.txt`; rerun log is
  `python-tests-final.txt`.
- No live Groq request, geography/model download, software installation, system
  configuration change, commit, push or submission was performed in this milestone.

## Exact rules and remaining submission blockers

The expanded [official event rules](https://hackathon.genai.works/event/open-agent-hackathon-2026)
require Zetaris **and** Meterless for all tracks (5.1), one primary track, and
declaration of pre-existing components. Cursor is optional. Section 5.2 asks for
NVIDIA technology where it contributes; NVIDIA use is not established here, and
Nemotron is not stated as the universal model requirement. Confirm the applicable
NVIDIA expectation with organizers rather than claiming unsupported compliance.
Track 02 fits evidence-backed investigation, but the demonstrated workflow is
**deterministic**, not a completed hosted-agent run. LangGraph capabilities remain
intact; the last hosted run was limited and Phase 4E's budget fix is offline-tested.
A genuine completed agent investigation still needs separate bounded verification.

Rule 4.1 closes the build window at **27 October, 23:45 UTC (28 October,
04:45 PKT)**, while the banner says 23:59. Use the earlier time. Required materials
include a **1–4 minute video**, slide deck and GitHub repository with setup/usage
instructions and an explanation of sponsor use (6.1–6.4). These materials are not
completed or submitted. No GitHub remote/published repository is established in
this checkout. A fresh-machine setup has not been tested. See
[the runbook](docs/hackathon-demo.md) for cache, dependency and vendor-source
packaging requirements; do not distribute credentials.

The separately announced Zetaris Demo Challenge is a different submission with
its own rules; this milestone does not establish eligibility or enter it.

## Zetaris: specific next action for the owner

Your Hobby account has **zero active computes**, with no verified instance or SQL
endpoint. No Zetaris settings are present in this session and no Zetaris query
has run. Account creation alone does not provide a running query engine.

Official [deployment choices](https://github.com/zetaris/getting-started/blob/main/docs/install/choose-install.md)
describe local Docker/WSL2 or an AWS cluster. Local guidance recommends 8 GB for
Docker, four CPUs and at least 15 GB disk. The [Cloud pricing page](https://www.zetaris.com/cloud)
says Hobby software is free but infrastructure is charged by the cloud provider.
No AWS deployment or paid compute was activated. Local installation remains
outside this milestone and requires your explicit approval and resource checks.

**Preferred action:** ask the organizers for an authorized running sandbox with
query/source-registration permission, its non-secret UI origin and organization
ID. Put credentials only in a private process environment. If they cannot provide
one, choose whether to authorize the official local setup; do not activate cloud
compute assuming Hobby means zero infrastructure cost.

Once a working instance exists, verify a read-only query using the
[official connection helpers](https://github.com/zetaris/getting-started/blob/main/scripts/HOWTO.md),
then connect real LifelineTwin infrastructure and environmental evidence for an
investigation query. The UI-proxy helper needs the UI origin, organization ID and
private authentication; direct REST/JDBC uses a different route. No speculative
adapter or fake response is presented as integration. **Zetaris is still the
blocking mandatory sponsor integration.**
