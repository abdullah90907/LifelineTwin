# Continuity workflow release

30 October 2026, Asia/Karachi.

The default view now supports hospital-access continuity cases for Houston and the Tuscaloosa–Northport–Moundville corridor in West Alabama. The advanced Houston map remains at `/explore`.

## Implemented

- Separate, checksum-verified regional datasets and region-scoped case lists.
- Three named Houston reference points and 210 named Alabama reference points; no point-to-population conversion.
- Emergency-service subsets based on public operator documentation: Ben Taub/Houston Methodist and DCH Regional/Northport. Live acceptance, capacity and availability are not verified.
- Explicit facility-outage and exact-road-restriction inputs, labeled exercises or unverified user reports.
- Before/after distances, alternative destinations, loss of access within the graph, and comparisons of restoration options.
- Optional proposed temporary-site comparison with explicit location-only limitations.
- Region-specific Open-Meteo/NWS context, checked separately from outage/restriction assumptions. Attaching an alert does not change the road graph.
- Persistent case inputs/results, source timestamps, input checksums and Markdown brief downloads.
- Additive `continuity_cases` database table; existing investigation records are retained.

## Executed browser verification

A real Edge browser created a case in each region, selected a proposed temporary location, exported the brief, reloaded the page and reopened the saved record. No browser page errors or mobile page overflow were recorded. Screenshots were inspected.

Recorded exercises:

- Houston / Ben Taub outage: one of three named reference points has a longer route; largest increase 1,012.250 metres.
- Alabama / DCH Regional outage: 105 of 210 named reference points have longer routes; largest increase 6,734.081 metres. None is newly disconnected within the snapshot.
- Alabama / DCH service restoration: 105 reference-point routes improve, with mean reduction 4,408.146 metres among those improved routes.
- Alabama / proposed Moundville service location: four reference-point routes improve by a mean 13,032.267 metres under the location-only proxy. This is not a verified emergency-care deployment option.

Raw case JSON, exported briefs, captures and the browser summary are under `evidence/continuity-release/`. These are hypothetical exercise results, not reports of actual hospital outages or affected residents.

## Verification coverage

Frontend tests exercise source failure handling, regional switching, exact case inputs, exports and duplicate-write safeguards. Backend tests exercise known-distance outage/road cases, destination filtering, snapshot mismatch rejection, alert-context handling, regional isolation, restart persistence and exports. Existing advanced backend and frontend regressions were also run; the production frontend build passed.

## Remaining limits

Population exposure, verified live closure ingestion, dynamic hospital capacity, clinical suitability for a particular patient, travel-time/traffic modeling, clean-machine installation and operational stakeholder validation are not established. Bounded coverage and an intentionally limited facility subset can omit external alternatives. Event timestamps record provenance; historical network conditions are not reconstructed.
