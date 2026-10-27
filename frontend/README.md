# LifelineTwin frontend · Phase 5A

Local React/TypeScript research workspace. No account, tile-service key or hosted
LLM credential is required. Start the existing backend in one terminal:

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin'
.\.venv-migration\Scripts\python.exe -m uvicorn lifelinetwin_backend.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```powershell
Set-Location 'D:\Projects 2026\LIfelineTwin\frontend'
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Node 20.19+ / 22.12+ is required by the selected Vite
release; verified here with Node 20.20.2. `npm run build` performs TypeScript checks
and emits `dist/`; `npm test` runs the frontend contracts and interaction tests.
Tests use real saved baseline/cache fixtures and mocked HTTP, with clearly
labeled test-only incident fixtures. They never call a hosted model or persist
test incidents to the application database. Windows sandbox restrictions may
require running tests in a normal terminal with TEMP/TMP in a writable directory.

## Architecture and boundaries

- `src/api.ts`: Zod-validated response subsets, typed read methods, cancellation
  and sanitized errors. `VITE_API_BASE` is public; never put secrets in VITE_*.
- `src/main.tsx`: QueryClient and browser router; no polling, automatic retries
  or focus refetch. Queries are cached and refreshed explicitly.
- `src/App.tsx`: application shell and route registration. `src/pages/` contains
  overview, atlas, incidents and intelligence views; `src/hooks/useWorkspace.ts`
  owns shared queries. `src/features/` holds incident browsing/history and the
  reusable intelligence layer stack. No write/inference/agent execution controls
  in this phase.
- `src/components.tsx`: identity, tags, errors, section headings and cached SVG map.
- `src/styles.css`: paper/forest/coral identity, responsive composition, focus
  treatment and reduced-motion overrides. Fonts are self-hosted npm assets.
- `public/data/heidelberg-atlas.json`: generated display geometry from the original
  checksum-verified cache. Regenerate from the repository root with
  `.venv-migration/Scripts/python scripts/export_frontend_atlas.py`; this reads
  existing data, never downloads geographic data or changes calculations.
- `qa.html`: development-only viewport harness, excluded from the default
  production build. Supports 1440/1024/768/390-pixel iframe viewports for manual QA.

The map uses local geometry and the existing GET `/analysis/baseline` endpoint.
Its route visualization joins original route nodes; it is not a navigation map.
No tiles, travel-time claims, verified closures or current facility capability
are inferred. The displayed mean averages only reachable sampled grid origins.
Cache presence is distinguished from inference/provider readiness.

Incident lists use 12-record pagination. Details load the most recent 20 records
per investigation pipeline. An empty database stays empty; historical verification
databases are not imported. A native dialog provides modal focus/escape behavior.

Vite proxies `/api` to loopback port 8000 so no backend CORS change is needed.
For production, configure a same-origin reverse proxy for `/api` (strip prefix),
SPA fallback to `index.html`, and static caching. The static build alone is not a
backend deployment. A different cross-origin API needs deliberate backend CORS
configuration, which this phase does not add. The API contract link uses the
same configured API base and opens OpenAPI JSON.

See `../PHASE5A_REPORT.md` for actual verification and next-phase scope.
