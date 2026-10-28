# Showcase audit

29 October 2026, Asia/Karachi.

## Houston implementation update

The findings below describe the earlier Heidelberg prototype. The active application now targets Houston's Texas Medical Center and Brays Bayou area. A real Edge browser verified labelled OSM tiles, road-name search, manually supplied closure endpoints, the current-weather/outlook screen, and a complete saved investigation. Screenshots and JSON are in `evidence/houston-showcase/`.

The real Houston dataset has 2,804 nodes, 7,161 directed edges, 25 origins, and 12 tagged hospital records. The three-segment sampled-centrality stress test increased distances for four origins; O5 gained 343.008 metres. All 25 remained connected. Investigation `4a247482-f668-433e-9ab7-0971e800b983` completed with 96 local TTM predictions. No browser page errors were recorded. Current weather and NWS alerts were retrieved separately from the hypothetical road analysis.

Large-network stress tests now use reproducible 128-source sampled edge betweenness (seed 42), because exact all-source calculation exceeded the interactive request budget. This approximation is recorded in closure metadata and documented in the UI and README. Manual closures use exact shortest-path calculations.

The earlier gaps for map context, direct road selection, and browser verification have been addressed for the Houston flow. Model skill evaluation, population-weighted access, verified road-status feeds, production deployment, clean-machine setup, and completed hosted-agent verification remain outside the demonstrated capability.

Actual WebGL context-loss recovery was also exercised in Edge. The compatibility map retained labelled tiles and analytical geometry on desktop and at 390-pixel mobile width. Its screenshots were inspected. Regression verification passed 32 frontend tests, 16 historical backend tests, and four current-feed tests; the production frontend build passed. The browser verification script requires Playwright and Edge; `LIFELINETWIN_PLAYWRIGHT` can point to a bundled Playwright package.

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
