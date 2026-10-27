# Phase 2.5: Geographic Scenario Validation

Completed 2026-10-24 (Asia/Karachi). Builds on Phase 2 without modifying it. Uses identical cached OSM data, adds a betweenness-driven closure-selection method, audits hospital records, quantifies snap offsets, and adds 18 new regression tests. No frontend, forecasting, AI model, or Phase 3 work performed.

## Dataset (unchanged from Phase 2)

**Central Heidelberg, Germany** — bounding box west/south/east/north `(8.650, 49.395, 8.705, 49.435)`, ~4 × 4.5 km. Cached 2026-10-24T16:15:39 UTC. Graph: **1,060 nodes, 2,331 directed edges**. Source: OpenStreetMap contributors via OSMnx 2.1.1; [ODbL](https://www.openstreetmap.org/copyright). Cache verified by SHA-256; no network request during analysis.

---

## Phase 2 baseline independently verified

Re-running `analyze` with the exact Phase 2 closure set reproduces identical results:

| Origin | Baseline m | Closures m | Increase m |
|---|---:|---:|---:|
| O1 | 2166.9 | 2213.4 | 46.5 |
| O2 | 1244.8 | 1244.8 | 0.0 |
| O3 | 489.2 | 489.2 | 0.0 |
| O4 | 18.4 | 18.4 | 0.0 |
| O5 | 885.0 | 885.0 | 0.0 |
| O6 | 749.5 | 749.5 | 0.0 |
| O7 | 1253.1 | 1253.1 | 0.0 |
| O8 | 788.8 | 800.5 | 11.7 |
| O9 | 694.7 | 694.7 | 0.0 |

Phase 2 report results confirmed. Verification command: `.venv/Scripts/python -m lifelinetwin_geo analyze`.

---

## Graph topology analysis

Run offline from cached GraphML:

| Property | Value |
|---|---|
| Weakly connected components | 11 |
| Strongly connected components | 26 |
| Largest WCC | 1,042 nodes |
| Largest SCC | 996 nodes |
| Undirected bridges | 156 |
| Articulation points | 137 |

The graph has 10 small isolated components (roads near the bounding-box edge). The main component contains all 9 origins and all 17 distinct hospital routing nodes. The 156 undirected bridges include many peripheral dead-end streets serving single buildings; closing them does not affect hospital access for any of the 9 grid origins. Bridge count alone is not a useful indicator of accessibility impact — the first three alphabetically-sorted bridges closed in an earlier draft produced **zero route-distance change**. This informed the switch to betweenness-filtered selection.

**Baseline route edges used**: 82 distinct undirected pairs appear in at least one of the 9 baseline shortest paths.

**Edge betweenness centrality** (length-weighted, directed, normalized): top entries are segments of Brückenstraße (score ≈ 0.164) and Mittermaierstraße/Berliner Straße/Ernst-Walz-Brücke (scores 0.145–0.158). The Mittermaierstraße corridor carries very high betweenness but is **not used by any of the 9 baseline routes** (those origins all approach from the north/east; Mittermaierstraße crosses the Neckar to the south). Brückenstraße (33811019 ↔ 928125779) is the highest-betweenness segment **actually traversed** by a baseline route.

---

## Phase 2.5 closure scenario

### Selection method

Candidate pairs ranked by **aggregated directed edge betweenness centrality** (length-weighted, normalized). Filtered to pairs: (1) present in at least one baseline route, (2) not already used in Phase 2, (3) non-adjacent (no shared node endpoints), (4) existing in the directed graph. Ties broken by sorted node-ID pair — fully deterministic. No hardcoded desired outcome.

### Selected closures

All three are **hypothetical only**, not reports of real events.

| ID | Street | Endpoints (OSM node IDs) | Betweenness score | Selection basis |
|---|---|---|---|---|
| D1 | Brückenstraße | 33811019 ↔ 928125779 | 0.163882 | Highest baseline-used pair |
| D2 | Bismarckstraße | 60697812 ↔ 146000024 | 0.095757 | 2nd-highest baseline-used |
| D3 | Bismarckstraße | 60697818 ↔ 298538536 | 0.082947 | 3rd-highest, non-adjacent to D2 |

**D1 (Brückenstraße)** is a segment of the old bridge road across the Neckar in central Heidelberg — geographically meaningful as a cross-river link. **D2 and D3** are two consecutive simplified junctions along Bismarckstraße, the main artery connecting the southern hospital cluster (St. Josefskrankenhaus, ATOS clinics) to the grid origins.

Each closure removes all parallel edges in both directions between the endpoint pair. Adjacent carriageways with different endpoints are not automatically closed. This is a network-model simplification, not physical road geometry.

---

## Before-and-after accessibility (Phase 2.5 scenario)

Shortest **network distance in metres**, not travel time. All three closures simultaneous and hypothetical.

| Origin | Baseline m | Disrupted m | Increase m | Note |
|---|---:|---:|---:|---|
| O1 | 2166.9 | 2166.9 | 0.0 | |
| O2 | 1244.8 | 1244.8 | 0.0 | |
| O3 | 489.2 | 489.2 | 0.0 | |
| O4 | 18.4 | 18.4 | 0.0 | Snap offset 285 m; see below |
| O5 | 885.0 | 885.0 | 0.0 | |
| O6 | 749.5 | **1515.3** | **+765.8** | Bismarckstraße bottleneck |
| O7 | 1253.1 | 1253.1 | 0.0 | |
| O8 | 788.8 | 788.8 | 0.0 | |
| O9 | 694.7 | 694.7 | 0.0 | |

- **Newly disconnected origins: 0** (9/9 remain reachable).
- **O6 route increase: +765.8 m (+102%)** — origin at grid point (8.694°E, 49.415°N) snapped to node 267161325, snap offset 19.5 m. Its baseline route to the nearest hospital used Bismarckstraße. With D2 and D3 both closed, the route reroutes via a much longer path to reach the next-nearest facility.
- **Mean baseline**: 921.2 m. **Mean disrupted**: 1006.2 m (+85.1 m, +9.2%). Means are per-origin averages including all 9 origins equally.

---

## Restoration ranking

Each restoration reopens **one segment only**, leaving the other two closed (independent evaluation). Ranked: (1) reconnected origins, then (2) distance saved among already-reachable.

| Rank | Reopen | Reconnected | Distance saved |
|---|---|---:|---:|
| 1 | D1 | 0 | 0.0 origin-m |
| 2 | D2 | 0 | 0.0 origin-m |
| 3 | D3 | 0 | 0.0 origin-m |

**All three individual restorations save 0.0 m.** This is a genuine result, not a bug. The O6 route increase is a **compound bottleneck effect**: it requires D2 AND D3 to be closed simultaneously to force the reroute. Reopening either D2 alone (D1+D3 still closed) or D3 alone (D1+D2 still closed) does not restore O6's baseline route, because the remaining Bismarckstraße closure still blocks the short path. The ranking tie is broken alphabetically by closure ID.

This demonstrates a real limitation of the independent-restoration ranking: when a disruption is caused by two non-adjacent closures acting together, individual restoration evaluations cannot distinguish which is more important. Both D2 and D3 must be reopened together to recover O6. D1 is unrelated to O6's disruption.

**Practical implication (hypothetical only):** If this scenario represented real simultaneous incidents on Bismarckstraße, re-opening either segment alone would not restore the blocked route; both would need to be cleared.

---

## Hospital record audit

27 OSM `amenity=hospital` records, 17 distinct routing nodes (multiple records share a node due to campus buildings mapped separately).

### Routing-node duplicates (5 groups)

| Routing node | Records sharing it |
|---|---|
| 11247645 | Klinik für Allgemeine Psychiatrie, Ethianum |
| 21697660 | Institut für Humangenetik, Frauenklinik, Hautklinik, Kinderklinik |
| 278914938 | Heidelberger Ionenstrahl-Therapiezentrum, Nationales Centrum für Tumorerkrankungen, Universitätsklinikum Heidelberg |
| 281086737 | Klinik für Allgemeine Innere Medizin und Psychosomatik, Zentrum für Schmerztherapie und Palliativmedizin, Innere Medizin X: Klinik für Nephrologie |
| 283220775 | Kopfklinik, Tropenmedizinische Ambulanz / HIGH / Zentrum für Infektiologie, Medizinische Klinik |

Duplicate routing nodes do **not** inflate the facility target set — `accessibility()` deduplicates to a set of node IDs before routing. The 27 records effectively represent 17 distinct routing destinations.

### Facility classification (keyword heuristic — not authoritative)

OSM `amenity=hospital` includes a wide range: general hospitals, university specialist clinics, research institutes, and residential buildings on hospital campuses. A keyword scan of the OSM `name` field classifies:

- **Likely general/emergency-capable** (~16 records): Kurpfalzkrankenhaus, St. Josefskrankenhaus, Salem, Klinik Sankt Elisabeth, ATOS Klinik, Unfallchirurgie-ATOS, Chirurgische Klinik, Frauenklinik, Hautklinik, Kinderklinik, Kopfklinik, Medizinische Klinik, Universitätsklinikum Heidelberg, and unnamed records.
- **Likely specialist/research/non-emergency** (~11 records): Institut für Humangenetik, Heidelberger Ionenstrahl-Therapiezentrum, Nationales Centrum für Tumorerkrankungen, Klinik für Allgemeine Psychiatrie, Zentrum für Schmerztherapie und Palliativmedizin, Institut für Psychosomatische Kooperationsforschung und Familientherapie (Personalwohngebäude), Tropenmedizinische Ambulanz / HIGH, Kinder- & Jugendpsychiatrie Heidelberg, Ethianum, Zentrum für Psychosoziale Medizin.

**This classification is a heuristic only.** It is not an independent medical/operational verification. All 27 records are retained in routing to maximise coverage; restricting to confirmed general hospitals would increase measured distances, especially for origins whose nearest routed node currently maps to a specialist clinic. That sensitivity analysis is not performed here.

**Snap distances to the nearest road node** range from 32 m (Institut für Psychosomatische Kooperationsforschung) to 329 m (Zentrum für Schmerztherapie und Palliativmedizin). High snap distances indicate facility points far from driveable roads — common for campus buildings set back from the street. These offsets are not included in route distances but would add to real access time.

---

## Snap-offset quantification

| Origin | Geographic point | Snapped node | Snap offset | Flag |
|---|---|---|---:|---|
| O1 | 8.661°E, 49.403°N | 3100180496 | 77.7 m | |
| O2 | 8.677°E, 49.403°N | 269790906 | 44.9 m | |
| O3 | 8.694°E, 49.403°N | 260807376 | 100.3 m | |
| O4 | 8.661°E, 49.415°N | 283751939 | **284.9 m** | Large offset |
| O5 | 8.677°E, 49.415°N | 281572580 | 58.1 m | |
| O6 | 8.694°E, 49.415°N | 267161325 | 19.5 m | |
| O7 | 8.661°E, 49.427°N | 772443402 | 58.3 m | |
| O8 | 8.677°E, 49.427°N | 1341408296 | 48.8 m | |
| O9 | 8.694°E, 49.427°N | 267040686 | **203.5 m** | Large offset |

**O4 (284.9 m snap offset):** The 3×3 grid point at the western-middle-north position falls in an area with sparse road coverage (likely a hillside or park edge near the bounding box). The nearest driveable node is 285 m away. O4's reported route distance of 18.4 m measures from that snapped road node to the nearest hospital node — it does not include the 285 m walk/access from the true geographic point. Real access distance for O4 is at least 285 m + 18.4 m ≈ 303 m, though the actual walking path is unknown. This origin is **not excluded** from analysis because its snapped node is valid and reachable; the limitation is documented here.

**O9 (203.5 m snap offset):** Similar issue at the eastern-north grid point. The true geographic point is 203 m from the road network.

**Facility snap offsets:** 13 of the 27 hospital records have snap offsets above 70 m; the maximum is 329 m (Zentrum für Schmerztherapie). Route distances measure between road nodes and do not include the final pedestrian/access leg from road node to hospital entrance.

These are not errors — they are an inherent limitation of matching geographic points to a simplified road network. Resolving them would require verified entrance coordinates and pedestrian/driveway access paths.

---

## Verification and reproduction

Tested on Windows 11 / Python 3.14.4 / OSMnx 2.1.1 / NetworkX 3.7. From the project root with the completed cache and `.venv` active:

```powershell
# Verify Phase 2 baseline is unchanged:
.venv/Scripts/python -m lifelinetwin_geo analyze

# Run Phase 2.5 analysis (capture evidence):
.venv/Scripts/python scripts/capture_phase25.py

# Run full test suite (30 tests):
.venv/Scripts/python -m unittest discover -s tests -v
```

**Test results:** 30 tests, 0 failures, 0 errors. 12 tests from Phase 2 (`test_geo.py`): 11 synthetic + 1 real-cache. 18 new tests from Phase 2.5 (`test_geo_25.py`): 7 synthetic unit tests for `choose_closures_by_betweenness`, 5 synthetic for `analyze_25`, 6 real-cache integration tests. All real-cache tests block HTTP via mock patch.

Evidence files:
- `evidence/phase2-5-cli.txt` — CLI output
- `evidence/phase2-5-results.json` — full route detail
- `evidence/phase2-5-graph-analysis.json` — topology metrics and betweenness rankings
- `evidence/phase2-5-tests.txt` — test runner output

---

## Files changed (Phase 2.5 additions only)

| File | Status | Description |
|---|---|---|
| `lifelinetwin_geo/analysis_25.py` | **New** | `choose_closures_by_betweenness` and `analyze_25` functions |
| `lifelinetwin_geo/__main_25__.py` | **New** | Standalone CLI entry for Phase 2.5 |
| `tests/test_geo_25.py` | **New** | 18 regression tests (7 unit + 5 unit + 6 real-cache) |
| `scripts/capture_phase25.py` | **New** | Evidence capture script |
| `evidence/phase2-5-cli.txt` | **New** | Observed CLI output |
| `evidence/phase2-5-results.json` | **New** | Full route/restoration JSON |
| `evidence/phase2-5-graph-analysis.json` | **New** | Topology analysis output |
| `evidence/phase2-5-tests.txt` | **New** | Test runner output |
| `PHASE2_5_REPORT.md` | **New** | This report |

No existing files were modified. Phase 2 closure results, `engine.py`, `data.py`, `__main__.py`, `test_geo.py`, and all evidence from Phase 1 and Phase 2 are preserved.

---

## Assumptions and limitations

1. **Distance ≠ travel time.** No speeds, traffic, or turn restrictions modelled.
2. **Bounding box excludes external hospitals.** Origins near the box edge may prefer real hospitals outside the study area; the fixed bbox causes artificial path constraints.
3. **Origins are an unweighted geographic grid**, not population-weighted demand. Equal weight per origin is a simplification.
4. **Compound-bottleneck restoration limitation.** The independent-restoration ranking cannot distinguish which of D2/D3 is more critical because each alone is insufficient; both must be reopened. This is a known limitation of the independent-closure evaluation approach used in both Phase 2 and Phase 2.5.
5. **Hospital facility classification is a keyword heuristic only.** Whether any given OSM record represents a currently operating emergency department requires independent verification.
6. **Snap offsets.** Large offsets (O4: 285 m, O9: 204 m; hospital snaps up to 329 m) mean reported route distances undercount real access distance. Hospital entrances and actual vehicle access paths are not modelled.
7. **OSM data snapshot.** Road network reflects OSM state at download time (2026-10-24T16:15 UTC). Real-world changes are not captured.
8. **Phase 2.5 closures are hypothetical.** D1, D2, D3 are not reports of real incidents. They are selected by graph analysis to stress the network in a scientifically reproducible way.
9. **Meterless persistence limitation** and **Zetaris blocked status** from Phase 1 remain unresolved and are outside Phase 2.5 scope.

---

## Remaining blockers

- **Zetaris:** still unconfigured. No SQL executed against a real Zetaris instance.
- **Meterless persistence-reopen:** still fails with exit 1 (documented Phase 1 limitation).
- **Hospital entrance/access validation:** geometric snapping not field-verified.
- **Compound restoration:** independent ranking cannot credit joint restorations.

Stopped at Phase 2.5. Phase 3 not started.
