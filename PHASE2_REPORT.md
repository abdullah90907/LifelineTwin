# Phase 2: geographic intelligence engine

Completed 2026-10-24 (Asia/Karachi). Real-data baseline, hypothetical closures, independent restorations, and automated tests are demonstrated. No frontend, forecasting, AI model, or Phase 3 work was performed. Phase 1 report and verified Meterless tests were preserved; README has an appended Phase 2 section.

## Dataset and implementation

**Central Heidelberg, Germany**, approximately 4 × 4.5 km. Bounding box west/south/east/north: `8.650, 49.395, 8.705, 49.435`. Source: OpenStreetMap contributors via OSMnx 2.1.1 and Overpass; [ODbL attribution](https://www.openstreetmap.org/copyright).

Cached **1,060 nodes, 2,331 directed driving edges, nine origin nodes, and 27 OSM `amenity=hospital` records at 17 distinct road nodes**. Records include St. Josefskrankenhaus, Kurpfalzkrankenhaus, Salem, and university hospital facilities. These are OSM classifications, not 27 independently verified emergency hospitals; some records represent campus buildings, specialist facilities, or duplicate geographic coverage.

Acquisition completed at 21:15:39 Karachi time (16:15:39 UTC). Snapshot and raw response cache occupy approximately 3.71 MB before the small attribution README. Files, source IDs, version, timestamp, and SHA-256 checksums are under [data/heidelberg](data/heidelberg/README.md).

The first Overpass request failed with **502 Gateway Timeout**, reporting full workers/queue; [exact error](evidence/phase2-download.txt). One retry after a 30-second pause succeeded: [download result](evidence/phase2-download-retry.txt). No synthetic graph was substituted for the real result. Dependency downloads also experienced delays/timeouts; a public-PyPI retry installed the isolated environment successfully. [Install log](evidence/phase2-install.txt) and [full version lock](requirements-phase2-lock.txt) are retained.

## Actual output

Shortest **network distance in metres**, not travel time. All three closures are simultaneous and **hypothetical**, not reports of real incidents.

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

Nine of nine origins reachable before and after closures; **zero newly disconnected**. Mean route distance increases from **921.2 m to 927.6 m**. Disconnection handling is exercised in synthetic unit tests; no real-network disconnection is claimed for this scenario.

Closures remove every parallel edge in both directions between these simplified junction pairs, not entire named streets:

- C1: Vangerowstraße, `11247599 ↔ 11247600`.
- C2: Iqbal-Ufer, `11247645 ↔ 645759168`.
- C3: Furtwänglerstraße, `13888159 ↔ 301109705`.

Each independent restoration leaves the other two segments closed. Ranking first maximizes reconnected origins, then summed distance savings among origins reachable in the fully disrupted case:

| Rank | Reopen | Reconnected origins | Summed distance saved |
|---|---|---:|---:|
| 1 | C2 | 0 | 13.2 origin-metres |
| 2 | C3 | 0 | 11.7 origin-metres |
| 3 | C1 | 0 | 0.0 origin-metres |

Benefits are conditional on the other closures and are not necessarily additive. [Full CLI output](evidence/phase2-cli.txt) and [JSON routes/results](evidence/phase2-results.json) preserve full-precision results and facility/source mappings.

## Assumptions and limits

Origins are an unweighted 3 × 3 geographic grid, not population demand. Facility geometry points and origins snap to nearest road nodes; offsets are recorded but excluded from route distance. **O4's 18.4 m route excludes its 285 m origin snap offset**. Facility offsets reach roughly 329 m. These are network-node accessibility measurements, not door-to-door access estimates; hospital entrances and physical barriers need validation before operational use.

Driving directions and edge lengths are retained. No speeds are invented. There are no traffic, travel-time, turn-restriction, emergency-service, capacity, restoration-cost, or construction-duration models. The bounding box excludes external hospitals and detours. All graph components are retained. Closure selection deliberately stresses baseline-used, nonadjacent links; it is not a forecast or representative risk sample. See [method details](docs/phase2-method.md).

## Verification and reproduction

Tested on Windows 11 / Python 3.14.4 with OSMnx 2.1.1 / NetworkX 3.7. The final suite contains 11 tiny synthetic algorithm tests plus one real-cache integration test. The real test prohibits HTTP, checks cache reuse, repeats analysis for identical results, and checks closure/restoration distance monotonicity. [Test output](evidence/phase2-tests.txt) records the final result. `pip check` also passed. The unchanged Meterless `npm run test:road` passed: [preservation evidence](evidence/phase2-meterless-preservation.txt).

From the project root, after creating `.venv` with `python -m venv .venv`:

```powershell
.venv/Scripts/python -m pip install --only-binary=:all: -r requirements-phase2-lock.txt
.venv/Scripts/python -m lifelinetwin_geo download
.venv/Scripts/python -m lifelinetwin_geo analyze
.venv/Scripts/python -m unittest discover -s tests -v
```

The completed cache makes `download` a verified no-op. Analysis and tests need no internet after dependencies are installed. A missing cache makes real-data testing explicitly skip; synthetic passes alone must not be reported as real-data completion.

Created `lifelinetwin_geo/{engine,data,__main__,__init__}.py`, `tests/test_geo.py`, dependency specification/lock, cached data/manifest/attribution, method notes, and Phase 2 evidence. The pure engine imports only NetworkX and the standard library, leaving sponsor integration modular.

**Remaining blockers:** none for this bounded Phase 2 demonstration. Zetaris remains unconfigured, and the previously documented Meterless persistence-reopen limitation remains unresolved. Geometric snapping and facility/service validation limit operational interpretation. Stopped before Phase 3.
