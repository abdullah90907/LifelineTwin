"""Phase 2.5 analysis: betweenness-driven closure selection.

Public API
----------
choose_closures_by_betweenness(graph, baseline, count, exclude_pairs) -> list[dict]
analyze_25(graph, origins, facilities, ...) -> dict

Extends engine.py without modifying it. Imports only NetworkX, standard library,
and engine.py. No OSMnx, no downloads, no credentials.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import networkx as nx

from .engine import accessibility, close_segments, analyze, compare


def choose_closures_by_betweenness(
    graph: nx.MultiDiGraph,
    baseline: list[dict],
    count: int = 3,
    exclude_pairs: Sequence[tuple[int, int]] | None = None,
) -> list[dict]:
    """Select hypothetical closure segments by length-weighted edge betweenness.

    Selection criteria (applied in order):
    1. Edge pair must appear in at least one baseline shortest-path route.
    2. Exclude pairs listed in exclude_pairs (e.g. Phase 2 closures).
    3. Pairs ranked by aggregated directed betweenness score (desc), then
       sorted node-ID pair (asc) for ties -- fully deterministic.
    4. Non-adjacency: once a node endpoint is consumed, no further pair
       sharing that node is accepted (prevents immediately adjacent closures).
    5. Edge must exist in the directed graph.

    Each returned dict contains:
        id, u, v, name, betweenness_score, selection_method, hypothetical.

    Raises ValueError if fewer than count qualifying segments are found.
    """
    exclude_set: set[tuple[int, int]] = set()
    if exclude_pairs:
        for u, v in exclude_pairs:
            exclude_set.add(tuple(sorted((int(u), int(v)))))

    # Pairs actually traversed by any baseline route
    used_pairs: set[tuple[int, int]] = set()
    for row in baseline:
        path = row.get("path", [])
        for a, b in zip(path, path[1:]):
            used_pairs.add(tuple(sorted((a, b))))

    # Directed edge betweenness (length-weighted).
    # NetworkX returns (u, v, key) tuples for MultiDiGraph.
    ebc_raw = nx.edge_betweenness_centrality(graph, weight="length", normalized=True)
    ebc_by_pair: dict[tuple[int, int], float] = defaultdict(float)
    for edge_key, val in ebc_raw.items():
        u, v = edge_key[0], edge_key[1]
        pair = tuple(sorted((u, v)))
        ebc_by_pair[pair] += val  # type: ignore[index]

    ranked = sorted(ebc_by_pair.items(), key=lambda kv: (-kv[1], kv[0]))

    selected: list[dict] = []
    used_nodes: set[int] = set()

    for (u, v), score in ranked:
        pair = (u, v)
        if pair in exclude_set:
            continue
        if pair not in used_pairs:
            continue
        if used_nodes.intersection({u, v}):
            continue
        if not graph.has_edge(u, v) and not graph.has_edge(v, u):
            continue
        edges = (
            list((graph.get_edge_data(u, v) or {}).values())
            + list((graph.get_edge_data(v, u) or {}).values())
        )
        names = sorted({str(d.get("name", "unnamed")) for d in edges})
        cid = f"D{len(selected) + 1}"
        selected.append({
            "id": cid,
            "u": int(u),
            "v": int(v),
            "name": "; ".join(names),
            "betweenness_score": float(score),
            "selection_method": "betweenness_baseline_used_nonadjacent",
            "hypothetical": True,
        })
        used_nodes.update({u, v})
        if len(selected) == count:
            break

    if len(selected) < count:
        raise ValueError(
            f"Only {len(selected)} qualifying closure segment(s) found; "
            f"{count} requested. Try reducing count or exclude_pairs."
        )
    return selected


def analyze_25(
    graph: nx.MultiDiGraph,
    origins: list[dict],
    facilities: list[dict],
    exclude_pairs: Sequence[tuple[int, int]] | None = None,
    closures: list[dict] | None = None,
    count: int = 3,
) -> dict:
    """Full Phase 2.5 pipeline.

    If closures is None, calls choose_closures_by_betweenness to select them.
    Otherwise uses the caller-supplied list (same format as engine.analyze).

    Returns a dict with the same keys as engine.analyze() plus:
        selection_method: str
    """
    baseline = accessibility(graph, origins, facilities)
    if closures is None:
        closures = choose_closures_by_betweenness(
            graph, baseline, count=count, exclude_pairs=exclude_pairs
        )
        method = "betweenness_baseline_used_nonadjacent"
    else:
        method = "caller_supplied"
    result = analyze(graph, origins, facilities, closures)
    result["selection_method"] = method
    return result
