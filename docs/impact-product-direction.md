# Product direction: hospital-access continuity planning

Research date: 29 October 2026 (Asia/Karachi).

## Implementation status — 30 October 2026

The main briefing workflow now supports Houston and the West Alabama corridor. Both have verified geographic snapshots, named reference points, an operator-documented emergency-service subset, regional weather/alert context, explicit exercise/user-report cases, outage comparisons, proposed temporary-site comparisons, SQLite persistence, and Markdown exports. The advanced Houston map can pass exact road selections into a case with snapshot validation.

The sections below retain the original research specification. Population estimates, an authorized live road-restriction feed, historical-state reconstruction, a separate advanced Alabama map, clinical capacity/acceptance data, and operational stakeholder validation remain unimplemented. See the repository README and `evidence/continuity-release/` for the implemented scope and actual verification records.

## Decision

Support Houston and an Alabama pilot in one system, organized around disruption cases and response decisions. Do not present switching road nodes or adding another city as the product's distinctive value.

The intended user is a regional emergency planner or healthcare coalition analyst. The question is: Which communities could lose access to appropriate care, and which feasible intervention preserves the most access?

Houston remains the implemented area. Tuscaloosa–Northport and surrounding rural catchments are a candidate Alabama pilot requiring geographic coverage and facility-data validation. Neither Alabama routing support nor population impact is implemented by this document.

## Lessons from real projects

| Reference | Documented approach | Implication for LifelineTwin |
| --- | --- | --- |
| WFP ADAM live map | Recent disaster events link to generated impact products and reports | Start from an event and a decision brief, not a network editor |
| World Bank GOSTnets | Network-based accessibility analysis, including health-facility access | Routing is a supporting analytical method; use it to evaluate service access |
| healthsites.io | Open facility data with community and institutional validation | A mapped hospital is insufficient: distinguish verified services, unknown capability, and stale information |
| IFRC RCHIS | Supports healthcare staffing and equipment planning using operational data | Useful actions concern continuity of care and resources, not simply displaying a detour |
| ALGO Traffic | Alabama road incidents, construction and traffic information | Investigate authorized feed access; a public website does not establish permission or a supported ingestion API |

Sources:

- https://docs.adam.geospatial.wfp.org/users/live-map/
- https://worldbank.github.io/GOSTnets/
- https://worldbank.github.io/GOSTnetsraster/health-and-disasters/
- https://campaigns.healthsites.io/about/
- https://www.ifrc.org/our-work/health-and-care/emergency-health/red-cross-and-red-crescent-health-information-system
- https://www.caps.ua.edu/wp-content/uploads/2019/04/CAPS_ALGOTraffic_20181025.pdf
- https://www.alabamapublichealth.gov/ruralhealth/at-a-glance.html

These references inform the proposed design. Their existence does not validate this project's effectiveness, operational readiness, or integration with those systems.

## Main workflow

1. **Review a case.** Select a real sourced event, a human-confirmed disruption, or an explicitly labelled exercise. Show the location, observation time, source and freshness.
2. **Assess care access.** Show named affected communities and suitable facilities. Use census-derived population only after geographic allocation and routing are verified. Do not relabel grid origins as communities or people.
3. **Compare interventions.** Compare restoring a road, excluding an unavailable facility, and pre-positioning a proposed temporary service point. Report the modeled access improvement, assumptions and information still needed.
4. **Issue a review brief.** Export a timestamped report explaining the event, supported consequences, alternatives, provenance and required human verification. A recommendation is not a dispatch order.

The map supports these steps. Road selection, node identifiers and layer controls move to an advanced investigation view.

## What live data can legitimately change

| Input | Supported use | Unsupported shortcut |
| --- | --- | --- |
| NWS warning | Identify the alert area and prioritize investigation of geographically overlapping services and corridors | Treat every road under the warning as closed |
| Gauge reading | Establish a timestamped river condition; compare with a documented local threshold | Infer road passability without a validated relationship |
| Confirmed road restriction | Apply an audited match to the road network and recompute access | Snap an ambiguous road name to an arbitrary segment |
| Confirmed facility outage | Exclude the affected verified service and recompute alternatives | Treat silence or a missing API response as closure |
| Population data | Estimate residents associated with affected origin areas, documenting allocation assumptions | Multiply equal-weight sample points by invented population |

Current LifelineTwin weather and alerts update panels. They do not currently modify the routing graph. Live impacts require the confirmed restriction/outage path above or a separately validated hazard-exposure model.

## Houston and Alabama together

Use a shared case schema and region-specific data adapters. A regional overview compares source freshness, active cases, affected service coverage, and unresolved verification tasks. It must not compare raw node counts as impact.

- Houston: urban medical-center access and multiple alternative facilities.
- Alabama candidate: rural care access across a sufficiently wide catchment, with facility services checked against authoritative records. A small downtown crop would miss the point.

Do not enable an Alabama analysis option until roads, catchment boundaries and facilities are loaded and tested. Current Houston results must never be reused under an Alabama label.

## Required evidence before an impact claim

- An auditable source for each actual restriction or outage, or an explicit exercise label.
- Hospital capabilities, verification time and a way to represent unknown status.
- Named geographic origin areas and transparent population allocation.
- Boundary checks so restricted study extents do not artificially remove alternate hospitals or roads.
- Validation of any travel-time assumptions against an independent routing reference. Distance alone is not ambulance response time.
- Scenario comparisons reproduced independently from the saved inputs.
- User review with an emergency planner or healthcare coalition analyst before claiming operational usefulness.

## Implementation order

1. Establish the bounded Alabama catchment and verify its facility and restriction sources.
2. Add regional case handling without mixing cached data, weather coordinates, incidents or results.
3. Add facility-service outage analysis and an evidence-led case brief.
4. Add population-backed care-access comparisons and intervention planning after geographic validation.
5. Connect authorized live disruption sources and validate event-to-network matching.
6. Evaluate whether an LLM adds measurable value for source triage or explanation. Numerical access and exposure calculations remain reproducible geospatial computations.

A better model name, a busier dashboard, or an extra region selector is not evidence of greater public benefit.
