# Run and demonstrate the investigation workflow

Use the existing `.venv-migration` Python 3.13 environment and Node 22.12+.
Node 24.22.1 was used for frontend tests and production builds on this laptop.
Keep both servers bound to localhost. There is no public-deployment authentication.

## Existing laptop

From the repository root, start the API:

```powershell
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
.\.venv-migration\Scripts\python.exe -m uvicorn lifelinetwin_backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
Set-Location frontend
npm run dev
```

Open http://127.0.0.1:5173. If needed, `npm ci` in `frontend` installs the locked
frontend dependencies; nothing here installs Docker, WSL or a sponsor platform.

The default SQLite file is `data/backend/lifelinetwin.sqlite3`. Preserve it.
For an isolated recording, set `LIFELINETWIN_DATABASE` to a new absolute `.sqlite3`
path before starting the API. Restart with the **same path** to retrieve records.
For alternative ports, Vite accepts `--port`; set `LIFELINETWIN_API_TARGET` to
the corresponding localhost API origin in the frontend terminal.

## Three-minute demonstration

1. Explore the cached Heidelberg network. Select O6 and show its nearest-hospital
   route. Explain that hospital records and road conditions are not operationally verified.
2. Open **Disruption lab**, leave three segments selected, and **Analyze disruption**.
   These are centrality-selected hypothetical closures, not a flood report.
3. Inspect the increased O6 route. Preview **D1 + D2** and compare it with the
   zero-benefit individual reopenings. These values are recomputed from the graph.
4. Scroll the left panel to **Investigate & preserve**. Give the scenario a title.
   Keep the historical cutoff `2026-10-24T19:55:49Z` for the supplied cache, then
   **Create saved investigation** once. Local TTM inference may take time.
5. Review consequences and alternatives. Scrub the 96-hour forecast and inspect
   source/model metadata. Cached estimates and pretrained predictions do not
   establish real road closures. Click an advisory citation to open its source.
6. Inspect **Scenario assumption memory**: real Meterless WorldModel facts,
   supersession and source provenance. This is hypothetical restoration-preview
   state; SQLite preserves the accepted projection. No upstream disk-reopen claim.
7. Open **Records**, select the incident and **Inspect evidence**. Restart the API
   using the same SQLite path and reopen the saved URL. No analysis rerun is needed.

This demonstrates the deterministic pipeline. Do not narrate it as a successful
autonomous hosted-agent run. Existing LangGraph endpoints and traces remain
available separately; no Groq call is made by these steps. The video still needs
real Zetaris integration before it can claim main-event sponsor compliance.

## Reproduction and packaging

```powershell
.\.venv-migration\Scripts\python.exe scripts/run_offline_regressions.py
Set-Location frontend
npm test
npm run build
```

`scripts/verify_saved_workflow.py ID --port 8000 --output NEW.json` reads an
existing investigation and checks its paths and restoration metrics directly
against the geographic engine. It does not start an investigation. After restart,
use a different output path plus `--compare NEW.json`; evidence files are never
overwritten by this script.

For another machine, use the migration documentation and requirements files:
`requirements-migration.txt`, `requirements-phase4a.txt`, and
`requirements-phase4b.txt`. The CPU Torch build needs the appropriate PyTorch CPU
package index as documented in the migration report. Transfer the original
`data/heidelberg` files and the existing `.runtime/huggingface/hub` TTM cache;
they are not synthesized or replaced by setup. Include attribution and model
license information. This milestone did **not** verify a fresh-machine installation.

Meterless is a separately checked-out official reference engine under
`vendor/Meterless`, pinned in this workspace at
`1742dec56a66e58eef9dda2d2b865823758ca8cd`. For a new authorized checkout where
`vendor/Meterless` does not already exist:

```powershell
git clone --filter=blob:none --sparse https://github.com/Meterless/Meterless.git vendor/Meterless
git -C vendor/Meterless sparse-checkout set engines/world-model
git -C vendor/Meterless checkout --detach 1742dec56a66e58eef9dda2d2b865823758ca8cd
npm --prefix vendor/Meterless/engines/world-model/reference ci
```

Do not replace an existing checkout. The integration invokes its
existing `tsx/dist/cli.mjs` using Node on PATH, or `LIFELINETWIN_NODE` if supplied.
It has a 15-second subprocess limit and no automatic retries. If that optional
runtime is missing, failed, or timed out, the saved result explicitly says
`unavailable`; the analytical investigation continues. Sponsor verification tests
require the real runtime. Vendor code is gitignored: source and setup must be
distributed or restored deliberately, not assumed to be in a future GitHub clone.

The frontend also uses a bundled local geographic atlas. Preserve the original
cache and run `scripts/export_frontend_atlas.py` when preparing a distribution; the UI
checks graph snapshot identity before displaying analytical overlays. The
MapLibre renderer uses local geometry without paid tiles or mandatory accounts.
