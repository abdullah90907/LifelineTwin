# LifelineTwin frontend

React and TypeScript interface for hospital-access continuity planning.

## Local development

Run the FastAPI backend on `127.0.0.1:8000`, then start this directory with:

```powershell
npm ci
npm run dev
```

Open http://127.0.0.1:5173/ for the Houston and West Alabama briefing workflow. The development server proxies `/api` to the local backend; `LIFELINETWIN_API_TARGET` can select a different local API origin.

## Views

- `/`: regional evidence, explicit facility-outage cases, named-place consequences, response comparisons, saved cases, and Markdown brief downloads.
- `/explore`: advanced Houston street map, exact road selection, disruption/restoration analysis, and transfer of selected roads into a continuity case.
- `/environment`: current Houston weather and local Granite forecasting controls.
- `/incidents` and `/investigations/:id`: existing advanced investigation records and evidence.

The briefing endpoints are region-scoped. Switching pilots clears the selected case and starts the region's form and queries independently. Source errors remain errors; missing alert data is not represented as zero alerts. User reports remain unverified, and temporary-site comparisons are location-only proxies.

`src/continuityApi.ts` validates the new API contracts with Zod. `src/pages/Continuity.tsx` implements the decision workflow. `src/continuity.css` contains its responsive layout. The older advanced map remains in `src/features/workspace/`.

## Verification

`npm test` runs the frontend regression suite; `npm run build` checks TypeScript and creates the production bundle. Tests use controlled HTTP and renderer adapters, rather than claiming live provider or GPU verification.

The repository's `scripts/verify_continuity_browser.cjs` exercises both pilots in a real Edge browser, saves cases, downloads briefs, reopens records, and checks mobile overflow. It requires Playwright and Edge; `LIFELINETWIN_PLAYWRIGHT` can point to a bundled Playwright package. Recorded captures are under `evidence/continuity-release/`.

A static frontend build alone is not a full deployment. Configure a same-origin API reverse proxy and SPA fallback when hosting it. The backend remains a local prototype without production authentication. See the repository README for data preparation, facility scope, limits, and source attribution.
