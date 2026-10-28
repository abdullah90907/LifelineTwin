# Showcase audit

29 October 2026, Asia/Karachi.

## Verdict

LifelineTwin has a working local analytical pipeline. It is suitable for explaining a small hypothetical hospital-access investigation, but this audit does not establish readiness for a professor-facing product demonstration or an operational decision system.

## Executed checks

- Started the actual FastAPI application on localhost:8000.
- GET `/health`: database OK; geographic and model caches present.
- GET `/analysis/baseline`: nine origin results returned.
- Called the geographic engine with three betweenness-selected closures: nine origin results, three closures, and three pair-restoration comparisons.
- POST `/analysis/environment` with the historical cutoff `2026-10-24T19:55:49Z`: real local `ibm-granite/granite-timeseries-ttm-r1` inference returned 96 temperature predictions.
- Repeated the environment API call for wind speed: 96 predictions in km/h.
- GET `/api/health` through Vite on localhost:5173: successful backend connection after running both local servers with networking access.
- Raw temperature and wind responses are saved as `evidence/showcase-audit-weather.json` and `evidence/showcase-audit-wind.json`.

The cutoff replays historical weather. These calls do not demonstrate current conditions, forecast skill, or road-closure detection. No hosted LLM was invoked. Frontend tests use controlled HTTP and renderer adapters; they are not browser or GPU verification.

## Gaps found and addressed

- Map initialization previously recovered only from some WebGL errors. Worker failures could leave the map initializing indefinitely. Renderer errors and a 12-second startup timeout now reveal the cached SVG compatibility map.
- The navigation label “Signals” concealed the weather feature. It now reads “Weather.”
- The weather interface exposed only temperature although the backend supports additional variables. It now offers temperature, wind speed, relative humidity, and pressure. Its request/cache key and chart labels track the selected variable.

The production frontend build passed. Regression tests cover controlled renderer failure recovery and the selected-variable request contract. These checks do not establish forecast accuracy or visual browser correctness.

## Remaining showcase gaps

1. **Browser validation:** manually verify actual WebGL rendering, fallback rendering, responsive layouts, and the complete save/reopen flow in the running browser. This audit does not claim that visual verification.
2. **Map context:** the map draws cached study-network geometry; a conventional labelled street basemap and broader geographic coverage are absent.
3. **Useful scenario input:** the visible disruption controls select a number of centrality-ranked segments. They do not provide direct arbitrary road selection by clicking the map.
4. **Evidence of model value:** compare forecasts against held-out observations and a persistence baseline, reporting MAE/RMSE. The model producing values alone does not establish accuracy or added value.
5. **Decision relevance:** nine equally weighted origins and nearest-hospital distance do not measure population served, hospital capacity, emergency response time, or repair cost.
6. **Agent completion:** a genuine completed LLM-selected investigation remains unverified. No fixed free hosted inference service is supplied by this implementation.
7. **Reproducibility:** a clean machine still needs separately prepared geographic, model, and Meterless runtime assets. The existing laptop environment is not proof of a reproducible installation.

The most defensible demonstration is a clearly bounded before/after road-access comparison with inspectable routes and restoration savings. A stronger claim needs the validation above rather than additional model names in the README.
