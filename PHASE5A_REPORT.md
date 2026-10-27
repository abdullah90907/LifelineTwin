# Phase 5A — Frontend Foundation

Date: 2026-10-26. Existing repository: `D:\Projects 2026\LIfelineTwin`.

## Delivered

A working local React/TypeScript frontend in `frontend/`, with a coherent product
identity, responsive application shell and four navigable destinations: Overview,
Atlas, Incidents and Intelligence. Real cached geometry and existing API results
drive the overview. No sample incidents, invented forecasts or simulated AI
conclusions populate the product.

This is a frontend foundation, not the full investigation application. The
existing backend, model/provider configuration, analytical engines, geographic
cache, history and prior evidence remain intact. No backend source modification,
new geographic download, training, login, infrastructure installation, publication,
commit or push was performed.

## Design research and decisions

Reviewed the three requested references before implementation:

- [Linear's design refresh](https://linear.app/now/behind-the-latest-design-refresh)
  informed quieter navigation, a clear distinction between orientation and work,
  and restrained separators. These principles are applied to a compact top nav
  and numbered content sections, without copying its layout.
- [Vercel's interface guidelines](https://vercel.com/design/guidelines) informed
  semantic links, visible keyboard focus, real loading/error feedback, accessible
  controls and reduced-motion handling.
- [Mapbox Studio](https://www.mapbox.com/mapbox-studio) informed a map-led identity
  with deliberate layer styling and useful geographic context. Mapbox itself is
  not a dependency; no tile-service account, token or paid service is required.

The chosen identity is a **research atlas**: warm paper backgrounds, a deep forest
cartographic field, soft mineral-green panels and a restrained coral route accent.
Manrope supplies precise interface headings; DM Sans supplies readable utility
text; an editorial serif italic introduces the overview. Fonts are self-hosted.
A custom linework brand mark suggests infrastructure, connected systems and a
twin. There are no avatars, fabricated notifications or generic KPI trends.

The primary reading order is purpose and study scope → geographic baseline →
incident workspace and intelligence capabilities → evidence principles. The map
anchors the product visually; navigation stays relatively quiet. Source age and
scientific limitations sit next to the results they qualify.

Motion is limited to short page entrances, first route drawing, hover feedback,
zoom transitions and genuine loading indicators. `prefers-reduced-motion` disables
animations and transitions. On narrow viewports, navigation remains accessible,
the map and summary stack, origin controls form a generous touch grid, and the
lower sections become a single column.

## Technology and structure

Verified runtime: Node 20.20.2 / npm 11.4.2. Installed dependencies are locked in
`frontend/package-lock.json`.

| Technology | Actual installed version | Role |
|---|---|---|
| React / React DOM | 19.3.1 | UI components |
| TypeScript | 5.9.3 | Strict type checking |
| Vite | 7.3.7 | Local server, same-origin proxy and static build |
| React Router | 7.18.4 | URL routes, direct entry and navigation |
| TanStack Query | 5.104.5 | Cached async server state and cancellation |
| Zod | 4.6.7 | Runtime validation of used API response fields |
| Lucide React | 0.468.0 | Consistent lightweight icon system |
| Fontsource variable fonts | 5.3.0 | Local DM Sans and Manrope assets |
| Vitest | 4.1.12 | Frontend tests |
| Testing Library / jsdom | 16.3.3 / 26.1.0 | DOM interactions and contracts |

`src/App.tsx` contains the shell and route registry. `src/pages/` separates the
four destinations; `src/features/incidents/` owns the read-only incident workflow;
`src/features/intelligence/` owns the reusable capability stack.
`src/hooks/useWorkspace.ts` owns common queries, `src/api.ts` is the reusable typed
API boundary, and `src/components.tsx` supplies shared primitives and the map.

No generic admin template, hosted UI builder, map SDK or animation runtime is
required. Custom SVG cartography keeps this initial dataset inspectable and
lightweight. Future modules can add data/interaction services without changing
the application shell or analytical engines.

## Actual functionality

### Overview and atlas

- Reads `/health`, `/analysis/baseline` and paginated `/incidents` through the
  frontend's same-origin `/api` proxy to the existing localhost backend.
- Shows API connectivity, actual road-node/edge counts, hospital records, reachable
  origins and mean nearest-facility distance. Missing API results show placeholders
  and actionable errors; cached map geometry can remain visible independently.
- The actual response contained **1,060 nodes, 2,331 directed edges, 27 hospital
  records and 9/9 sampled origins with a route**. Mean network distance was
  **921.1519721593538 m**, displayed as **921 m**. This averages reachable origins
  equally; it is not travel time, door-to-door access or clinical readiness.
- Select any of the nine origins to display its backend-computed baseline route.
  Browser verification selected O1 and showed **2.17 km**. O5 initially shows
  **885 m**. These labels are formatted API values, not hardcoded measurements.
- Zoom in/out/reset and hospital-layer visibility controls work. A dedicated
  Atlas view includes a legend, origin distances, limitations and a clearly
  labeled future scenario-editor boundary.
- `scripts/export_frontend_atlas.py` uses the existing checksum-verifying loader
  to export display-only geometry: **1,554 distinct display lines**, **257,582
  compact JSON bytes**. Opposite-direction duplicate display geometry is deduplicated;
  the original directed graph and calculations are not changed.
- Static and API manifests were compared and matched. OSM attribution, ODbL link
  and the **24 Oct 2026** snapshot date are visible. Route display joins original
  route nodes; it is not a turn-by-turn map or full edge-geometry route renderer.

### Incident workspace

- Reads actual local records, preserving hypothetical/user-reported/attributed
  verified distinctions and status. The connected database returned **zero
  incidents**, and the product shows an honest empty state.
- Twelve-record pagination has URL-backed offset state. Compact overview lists
  show at most three of the latest returned records; counts are labeled as shown,
  not presented as global totals.
- A selected incident opens a native modal with source text, context and saved
  deterministic/agent history, fetched from existing GET endpoints. History is
  limited to the 20 most recent entries per pipeline and does not launch a run.
- Because the real database is empty, populated detail/history behavior was
  verified using clearly labeled test-only HTTP fixtures, never inserted into the
  real database or shown as live-success evidence. Full result/trace exploration
  and incident creation/editing remain future work.

### Intelligence and API integration

- Describes geographic, Open-Meteo, local TTM and LangGraph capabilities with
  conservative statuses. Cache/weight presence is explicitly separated from
  successful inference or provider readiness.
- Does not invoke environmental inference, a hosted model, an agent or live data
  ingestion on mount or through any button in this phase. No provider key enters
  the frontend, public configuration or bundle.
- The API client validates used response fields, propagates abort signals and
  displays sanitized failures. Query retries, background focus refetch and polling
  are disabled. A refresh control deliberately refreshes backend queries.
- The Intelligence view explains provenance and human-review requirements and
  links to actual OpenAPI JSON through the configured API base. The proxy avoids
  changing backend CORS. Production requires an explicit reverse proxy and SPA
  fallback; the static build alone does not deploy the Python backend.

## Verification and actual results

**Final frontend tests: 12 passed, 1 test file.** Tests cover schema mismatch,
network-error sanitization, invalid JSON, abort propagation, real cache identity,
actual baseline origin selection, layer/zoom/reset controls, populated/empty/
unavailable states, navigation, missing routes, and read-only history retrieval
with escaped source text. Test incidents are explicitly synthetic fixtures only.

**Production build and strict TypeScript checks passed.** The final application
bundle is approximately **418.15 kB / 129.62 kB gzip**; CSS **31.41 kB / 9.92 kB
gzip**, plus local font files and the cached geometry JSON. These are build sizes,
not a Lighthouse or frame-rate benchmark. Rollup reports harmless upstream Zod
annotation warnings and removes those comments; compilation still succeeds.

**Nine read-only HTTP smoke checks passed**, each returning 200: four application
routes, health, baseline, incidents, OpenAPI and atlas data. The audit verifies
matching source/API/display manifests and records actual metrics. It performs no
write, forecast or agent requests. Evidence: `evidence/phase5a/http-smoke.json`.

**Browser review completed** in the in-app browser. A development-only `qa.html`
iframe harness exercised real CSS widths **1440, 1024, 768 and 390 pixels**;
rendered telemetry reported no horizontal overflow at all four widths. Desktop
captures are scaled to fit the preview pane; they are not full-resolution device
screenshots. Manual navigation, origin selection, layer toggle, zoom, mobile
controls and reading flow were checked. Screenshots are retained under
`evidence/phase5a/`. No comprehensive screen-reader/device/contrast audit or
automated reduced-motion emulation is claimed; semantic controls, native modal
behavior, focus handling and reduced-motion CSS are implemented.

**Final npm audit: zero vulnerabilities**, including development dependencies.
The initial test-runner range resolved to packages with advisories; the new
frontend test runner was upgraded to its patched 4.1.12 release and the audit
rerun. No existing Python dependencies were upgraded.

Initial test launches exposed Windows sandbox temporary-file restrictions and
test-loader/type issues. These were corrected; the successful frontend test run
used a normal permission context and repository-local TEMP/TMP. Chrome native
automation was unavailable, so verification used the functioning in-app browser
and local viewport harness. These initial issues are not concealed as passing
runs. The Python suite was not rerun for this frontend-only phase; its prior
130-pass Phase 4E result is historical, not a newly claimed result here.

Visual review improvements included removing an initial programmatic focus
outline, improving small-text contrast/readability, self-hosting fonts, adding
44px phone map/origin targets, strengthening the cartographic focal point,
correcting empty pagination and making API links proxy-compatible.

## Run and reproduction

Use separate terminals:

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
.\.venv-migration\Scripts\python.exe -m uvicorn lifelinetwin_backend.main:app --host 127.0.0.1 --port 8000
```

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin\frontend'
npm ci
npm run dev
# Open http://127.0.0.1:5173
```

Verification commands:

```powershell
# From frontend/
npm test
npm run build
npm audit
# From repository root, while both local servers run:
.\.venv-migration\Scripts\python.exe scripts/verify_frontend_http.py
```

Additional setup and architecture notes are in `frontend/README.md`. The QA
harness is development-only and excluded from the normal production build.

## Suggested next frontend work

1. Incident authoring with explicit evidence attribution, validation and status
   changes; complete investigation/result/trace browsing with pagination.
2. Approved hypothetical closure selection and before/after/restoration map
   comparisons, preserving existing deterministic computations.
3. On-demand environmental series and TTM forecast views with timestamps, units,
   provenance and a clear prediction boundary.
4. An explicit user-triggered agent investigation flow with bounded requests,
   honest limited/failed states and exact evidence navigation. Hosted completion
   still needs separate live verification; frontend presence does not establish it.
5. Expanded accessibility/performance audits and URL-persistent map state before
   adopting a richer map renderer for larger datasets.

Stopped at the frontend foundation. No remaining interactive modules were built
in full, and no real incident or AI success was fabricated.

Final delivery logs: `evidence/phase5a/frontend-tests-verified.txt` (12 tests in 3.00 seconds), `evidence/phase5a/build-verified.txt` (build in 4.57 seconds), and `evidence/phase5a/npm-audit.json` (zero vulnerabilities). Temporary verification servers were stopped after testing.
