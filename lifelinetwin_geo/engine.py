"""Pure NetworkX analysis. No downloads, credentials, or OSMnx side effects."""
import math
from numbers import Real
from collections import Counter
import networkx as nx


def validate_graph(graph):
    if not graph.is_directed() or not graph.is_multigraph():
        raise ValueError("Expected a directed MultiDiGraph")
    for _, _, _, data in graph.edges(keys=True, data=True):
        length = data.get("length")
        if not isinstance(length, Real) or not math.isfinite(length) or length < 0:
            raise ValueError("Every edge requires a finite nonnegative length in metres")


def accessibility(graph, origins, facilities):
    """Distance to nearest reachable facility, preserving one-way restrictions."""
    validate_graph(graph)
    if not facilities:
        raise ValueError("At least one facility is required")
    targets = sorted({f["node"] for f in facilities})
    if any(n not in graph for n in targets + [o["node"] for o in origins]):
        raise ValueError("Origin/facility node missing from graph")
    distances, paths = nx.multi_source_dijkstra(graph.reverse(copy=False), targets, weight="length")
    rows = []
    for origin in origins:
        node = origin["node"]
        reverse_path = paths.get(node, [])
        rows.append({"id": origin["id"], "node": node, "distance_m": distances.get(node),
                     "facility_node": reverse_path[0] if reverse_path else None,
                     "path": list(reversed(reverse_path))})
    return rows


def close_segments(graph, segments):
    """Close all parallel edges in BOTH directions between each endpoint pair.

    A segment is one simplified intersection-to-intersection link, not an entire
    named street. Paired carriageways with different endpoints remain separate.
    """
    result = graph.copy()
    for segment in segments:
        u, v = segment["u"], segment["v"]
        if not graph.has_edge(u, v) and not graph.has_edge(v, u):
            raise ValueError("Closure segment does not exist in original graph")
        for a, b in ((u, v), (v, u)):
            if result.has_edge(a, b):
                result.remove_edges_from([(a, b, key) for key in list(result[a][b])])
    return result


def choose_closures(graph, baseline, count=3):
    """Deterministic stress-test selection, biased toward baseline-used links."""
    counts = Counter(tuple(sorted((u, v))) for row in baseline
                     for u, v in zip(row["path"], row["path"][1:]))
    selected = []
    used_nodes = set()
    for pair in sorted(counts, key=lambda pair: (-counts[pair], pair)):
        if used_nodes.intersection(pair):
            continue
        selected.append(pair)
        used_nodes.update(pair)
        if len(selected) == count:
            break
    if len(selected) < count:
        raise ValueError("Insufficient baseline route segments")
    result = []
    for i, (u, v) in enumerate(selected, 1):
        edges = list((graph.get_edge_data(u, v) or {}).values()) + list((graph.get_edge_data(v, u) or {}).values())
        names = sorted({str(d.get("name", "unnamed")) for d in edges})
        result.append({"id": f"C{i}", "u": u, "v": v, "name": "; ".join(names),
                       "baseline_route_uses": counts[(u, v)], "hypothetical": True})
    return result


def compare(before, after):
    result = []
    for a, b in zip(before, after, strict=True):
        if a["id"] != b["id"]:
            raise ValueError("Mismatched origin order")
        old, new = a["distance_m"], b["distance_m"]
        result.append({"id": a["id"], "baseline_m": old, "scenario_m": new,
                       "newly_disconnected": old is not None and new is None,
                       "increase_m": new - old if old is not None and new is not None else None})
    return result


def analyze(graph, origins, facilities, closures=None):
    baseline = accessibility(graph, origins, facilities)
    closures = choose_closures(graph, baseline) if closures is None else closures
    if len({c['id'] for c in closures}) != len(closures):
        raise ValueError("Duplicate closure IDs")
    if len({tuple(sorted((c['u'], c['v']))) for c in closures}) != len(closures):
        raise ValueError("Duplicate closure segments")
    disrupted_graph = close_segments(graph, closures)
    disrupted = accessibility(disrupted_graph, origins, facilities)
    restorations = []
    for reopened in closures:
        remaining = [c for c in closures if c["id"] != reopened["id"]]
        restored = accessibility(close_segments(graph, remaining), origins, facilities)
        reconnected = sum(a["distance_m"] is None and b["distance_m"] is not None
                          for a, b in zip(disrupted, restored))
        saved = sum(max(0, a["distance_m"] - b["distance_m"])
                    for a, b in zip(disrupted, restored)
                    if a["distance_m"] is not None and b["distance_m"] is not None)
        restorations.append({"reopened": reopened["id"], "reconnected_origins": reconnected,
                             "distance_saved_m_for_already_reachable": saved, "accessibility": restored})
    restorations.sort(key=lambda r: (-r["reconnected_origins"], -r["distance_saved_m_for_already_reachable"], r["reopened"]))
    return {"baseline": baseline, "closures": closures, "disrupted": disrupted,
            "changes": compare(baseline, disrupted), "restorations": restorations}
