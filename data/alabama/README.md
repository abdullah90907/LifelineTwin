# West Alabama continuity pilot

Coverage: Tuscaloosa–Northport–Moundville corridor. Acquisition bbox (west, south, east, north): `-87.71, 32.97, -87.46, 33.29`.

The downloaded OpenStreetMap data produces a directed driving graph with 26,865 nodes and 66,035 edges. It contains 210 named place reference points and three mapped hospital records. Continuity cases use only DCH Regional Medical Center and Northport Medical Center, whose emergency services are documented by the operator: https://www.dchsystem.com/services/emergency-services/ . Bryce Hospital is not included in that emergency-care destination subset. Operator service descriptions do not establish live availability or capacity.

Named OSM places include towns, suburbs and hamlets. Their mapped coordinates are snapped to driving nodes; points more than 1,000 metres from the graph are excluded. These are not census centroids, complete community boundaries, or population estimates. Each reference point has equal analytical weight.

`prepare_alabama.py` acquires raw map data from the OSM API in bounded cells and splits cells when the API reports its node limit. It retains references needed for complete downloaded ways and deduplicates nodes and ways before graph construction. The driving-way filter excludes pedestrian and cycle paths and ways marked `access=no/private`. Hospital nodes and closed ways are retained; relations are not reconstructed. Some referenced ways extend outside the acquisition bbox. Alternative facilities and roads beyond the downloaded network may be omitted.

The manifest contains checksums for `roads.graphml`, `hospitals.geojson`, `facilities.json` and `origins.json`. Runtime loading verifies those checksums. Raw XML files remain local and are ignored by Git.

Data attribution: © OpenStreetMap contributors, ODbL — https://www.openstreetmap.org/copyright . This snapshot is suitable for bounded scenario analysis, not a verified hospital directory or a live traffic/closure feed.
