# Houston study area

Texas Medical Center and Brays Bayou, Houston, Texas, USA.

- Road bbox (west, south, east, north): `-95.43, 29.68, -95.36, 29.735`.
- Hospital acquisition bbox: `-95.408, 29.697, -95.383, 29.724`.
- Road snapshot: 2,804 nodes and 7,161 directed edges, from OpenStreetMap via OSMnx.
- Hospitals: 12 tagged nodes and closed ways retrieved from the OpenStreetMap API 0.6 map endpoint. Hospital relations are not reconstructed. Names and polygon geometry come from the downloaded records; routing uses their representative points snapped to road nodes.
- Origins: 25 equal-weight sampled locations on a five-by-five grid, snapped to the road graph.
- Weather: `weather/obs_current-context.json` contains the downloaded Open-Meteo context for local model inference. The live weather endpoint retrieves current conditions separately.

The manifest contains checksums for the geographic inputs. Do not substitute another city's geometry under these filenames. All geographic data is attributed to OpenStreetMap contributors under ODbL: https://www.openstreetmap.org/copyright . Weather data is sourced from Open-Meteo: https://open-meteo.com/ . Hospital records are not a verified capability or availability directory.

`prepare_houston.py` explicitly acquires missing assets and retains existing verified geography. Its road download uses Overpass; its hospital geometry uses the direct OSM map API. Large raw XML and HTTP acquisition caches remain local and are ignored by Git.
