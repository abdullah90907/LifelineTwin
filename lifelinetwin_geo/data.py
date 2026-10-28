"""Explicit online acquisition and verified offline cache loading."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import osmnx as ox
import numpy as np

BBOX = (8.650, 49.395, 8.705, 49.435)  # west, south, east, north
AREA = "Central Heidelberg, Baden-Wurttemberg, Germany"


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snap(graph, lon, lat):
    # Vectorized great-circle lookup for this small graph; no scipy/sklearn tree.
    nodes = list(graph.nodes)
    distances = ox.distance.great_circle(lat, lon, np.array([graph.nodes[n]["y"] for n in nodes]),
                                         np.array([graph.nodes[n]["x"] for n in nodes]))
    i = int(np.argmin(distances))
    return int(nodes[i]), float(distances[i])


def download(directory, bbox=BBOX, area=AREA, grid=(0.2, 0.5, 0.8)):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "manifest.json").exists():
        load(directory)
        return "Existing verified cache retained; no network request."
    ox.settings.use_cache = True
    ox.settings.cache_folder = directory / "http-cache"
    ox.settings.requests_timeout = 90
    ox.settings.overpass_memory = 268435456
    graph_file = directory / "roads.graphml"
    if graph_file.exists():
        graph = ox.load_graphml(graph_file)
    else:
        graph = ox.graph_from_bbox(bbox, network_type="drive", simplify=True, retain_all=True)
        ox.save_graphml(graph, graph_file)
    raw_file = directory / "hospitals.geojson"
    if raw_file.exists():
        import geopandas as gpd
        features = gpd.read_file(raw_file).set_index(["element", "id"])
    else:
        features = ox.features_from_bbox(bbox, tags={"amenity": "hospital"})
        features.reset_index().to_file(raw_file, driver="GeoJSON")
    facilities = []
    for index, row in features.sort_index().iterrows():
        point = row.geometry.representative_point()
        node, offset = snap(graph, point.x, point.y)
        name = row.get("name")
        if not isinstance(name, str):
            name = f"Unnamed OSM hospital {index}"
        facilities.append({"id": f"{index[0]}/{index[1]}", "name": name, "node": node,
                           "lon": point.x, "lat": point.y, "snap_distance_m": offset})
    if len({f["node"] for f in facilities}) < 2:
        raise ValueError("Need at least two distinct hospital routing nodes")
    origins = []
    west, south, east, north = bbox
    used = set()
    for fy in grid:
        for fx in grid:
            lon, lat = west + fx * (east-west), south + fy * (north-south)
            node, offset = snap(graph, lon, lat)
            if node not in used:
                origins.append({"id": f"O{len(origins)+1}", "node": node, "lon": lon, "lat": lat,
                                "snap_distance_m": offset})
                used.add(node)
    if len(origins) < 5:
        raise ValueError("Fewer than five distinct origin nodes")
    write_json(directory / "facilities.json", facilities)
    write_json(directory / "origins.json", origins)
    files = ("roads.graphml", "hospitals.geojson", "facilities.json", "origins.json")
    write_json(directory / "manifest.json", {"area": area, "bbox_wsen": bbox,
               "download_completed_utc": datetime.now(timezone.utc).isoformat(),
               "source": "OpenStreetMap via OSMnx/Overpass", "overpass_url": ox.settings.overpass_url,
               "attribution": "(c) OpenStreetMap contributors; ODbL https://www.openstreetmap.org/copyright",
               "osmnx": ox.__version__, "network_type": "drive", "weight": "length (metres)",
               "nodes": graph.number_of_nodes(), "directed_edges": graph.number_of_edges(),
               "sha256": {name: digest(directory / name) for name in files}})
    return f"Cached {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges, {len(facilities)} hospitals."


def load(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["sha256"].items():
        if digest(directory / name) != expected:
            raise ValueError(f"Cache checksum mismatch: {name}")
    return (ox.load_graphml(directory / "roads.graphml"),
            json.loads((directory / "origins.json").read_text(encoding="utf-8")),
            json.loads((directory / "facilities.json").read_text(encoding="utf-8")), manifest)
