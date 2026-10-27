# Heidelberg OpenStreetMap snapshot

Real OpenStreetMap data acquired on 2026-10-24 through OSMnx 2.1.1 / Overpass.

Attribution: **© OpenStreetMap contributors**. Data is available under the
[Open Database License (ODbL)](https://www.openstreetmap.org/copyright).

- `roads.graphml`: directed driving graph, 1,060 nodes / 2,331 edges; edge length in metres.
- `hospitals.geojson`: 27 raw `amenity=hospital` records (not 27 independent hospitals).
- `facilities.json`: source OSM IDs, names, representative points, snap offsets, and 17 distinct routing nodes.
- `origins.json`: 9 geographically distributed grid samples snapped to road nodes.
- `manifest.json`: bounding box, timestamp, source, versions, and checksums.
- `http-cache/`: original OSMnx cached Overpass responses.

Read `docs/phase2-method.md` from the project root for snapping, boundary, and service-type limitations. The derived scenarios are hypothetical; this dataset contains no verified closure or emergency feed. Preserve this snapshot for offline reproducibility.
