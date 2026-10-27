"""Phase 2.5 regression tests.

All tests use SYNTHETIC graphs; no real OSM data is required for the suite to
run.  The real-data integration test (OfflineRealData25Tests) is skipped unless
data/heidelberg/manifest.json exists -- identical pattern to test_geo.py.

Existing tests in test_geo.py are NOT modified or removed.
"""
import unittest
from unittest.mock import patch
from pathlib import Path
import networkx as nx

from lifelinetwin_geo.engine import accessibility, close_segments, analyze
from lifelinetwin_geo.analysis_25 import choose_closures_by_betweenness, analyze_25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_graph():
    """Linear chain 1->2->3->4->5 with back-edges for bidirectionality."""
    g = nx.MultiDiGraph()
    lengths = {(1, 2): 100, (2, 3): 200, (3, 4): 50, (4, 5): 300}
    for (u, v), w in lengths.items():
        g.add_edge(u, v, length=w)
        g.add_edge(v, u, length=w)
    return g


def _run_baseline(g, origins, facilities):
    return accessibility(g, origins, facilities)


# ---------------------------------------------------------------------------
# Unit tests for choose_closures_by_betweenness
# ---------------------------------------------------------------------------

class BetweennessClosureSelectionTests(unittest.TestCase):
    def setUp(self):
        # Graph: 1 <-> 2 <-> 3; facility at 3, two origins
        self.g = nx.MultiDiGraph()
        self.g.add_edge(1, 2, length=10)
        self.g.add_edge(2, 1, length=10)
        self.g.add_edge(2, 3, length=20)
        self.g.add_edge(3, 2, length=20)
        self.origins = [{"id": "a", "node": 1}, {"id": "b", "node": 2}]
        self.facilities = [{"node": 3}]

    def test_returns_correct_count(self):
        baseline = accessibility(self.g, self.origins, self.facilities)
        closures = choose_closures_by_betweenness(self.g, baseline, count=1)
        self.assertEqual(len(closures), 1)

    def test_closure_uses_baseline_used_edges_only(self):
        """All selected pairs must appear in at least one baseline route."""
        baseline = accessibility(self.g, self.origins, self.facilities)
        # Add an isolated dead-end edge not used by any route
        self.g.add_edge(1, 99, length=5)
        self.g.add_edge(99, 1, length=5)
        closures = choose_closures_by_betweenness(self.g, baseline, count=1)
        used_pairs = set()
        for row in baseline:
            path = row.get("path", [])
            for a, b in zip(path, path[1:]):
                used_pairs.add(tuple(sorted((a, b))))
        for c in closures:
            self.assertIn(tuple(sorted((c["u"], c["v"]))), used_pairs)

    def test_exclude_pairs_respected(self):
        baseline = accessibility(self.g, self.origins, self.facilities)
        # Exclude the highest-betweenness pair; next best should be selected
        first = choose_closures_by_betweenness(self.g, baseline, count=1)
        excluded = [(first[0]["u"], first[0]["v"])]
        second = choose_closures_by_betweenness(self.g, baseline, count=1,
                                                exclude_pairs=excluded)
        self.assertNotEqual(
            tuple(sorted((first[0]["u"], first[0]["v"]))),
            tuple(sorted((second[0]["u"], second[0]["v"]))),
        )

    def test_non_adjacency_enforced(self):
        # Use a larger graph with enough route segments for count=2 non-adjacent closures.
        # Chain: 1 <-> 2 <-> 3 <-> 4 <-> 5; facility at 5, origin at 1.
        # Baseline route uses edges (1,2), (2,3), (3,4), (4,5) - four distinct pairs.
        big = nx.MultiDiGraph()
        for u, v in [(1, 2), (2, 3), (3, 4), (4, 5)]:
            big.add_edge(u, v, length=10)
            big.add_edge(v, u, length=10)
        origins2 = [{"id": "x", "node": 1}]
        facilities2 = [{"node": 5}]
        baseline2 = accessibility(big, origins2, facilities2)
        closures = choose_closures_by_betweenness(big, baseline2, count=2)
        self.assertEqual(len(closures), 2)
        nodes_used = []
        for c in closures:
            nodes_used += [c["u"], c["v"]]
        # Non-adjacency: no node should appear in more than one selected closure
        self.assertEqual(len(nodes_used), len(set(nodes_used)))

    def test_insufficient_segments_raises(self):
        baseline = accessibility(self.g, self.origins, self.facilities)
        with self.assertRaises(ValueError):
            choose_closures_by_betweenness(self.g, baseline, count=99)

    def test_closure_dict_has_required_keys(self):
        baseline = accessibility(self.g, self.origins, self.facilities)
        closures = choose_closures_by_betweenness(self.g, baseline, count=1)
        for c in closures:
            for key in ("id", "u", "v", "name", "betweenness_score",
                        "selection_method", "hypothetical"):
                self.assertIn(key, c)
            self.assertTrue(c["hypothetical"])
            self.assertGreater(c["betweenness_score"], 0)

    def test_deterministic(self):
        baseline = accessibility(self.g, self.origins, self.facilities)
        run1 = choose_closures_by_betweenness(self.g, baseline, count=1)
        run2 = choose_closures_by_betweenness(self.g, baseline, count=1)
        self.assertEqual(run1, run2)


# ---------------------------------------------------------------------------
# Unit tests for analyze_25
# ---------------------------------------------------------------------------

class Analyze25Tests(unittest.TestCase):
    def setUp(self):
        self.g = nx.MultiDiGraph()
        # Two paths from O to H: short direct and long indirect via bottleneck
        # O(1) -[10]-> A(2) -[5]-> H(3)     direct
        # O(1) -[50]-> B(4) -[50]-> H(3)    indirect
        for (u, v, w) in [(1, 2, 10), (2, 1, 10), (2, 3, 5), (3, 2, 5),
                          (1, 4, 50), (4, 1, 50), (4, 3, 50), (3, 4, 50)]:
            self.g.add_edge(u, v, length=w)
        self.origins = [{"id": "O", "node": 1}]
        self.facilities = [{"node": 3}]

    def test_analyze_25_returns_engine_compatible_dict(self):
        result = analyze_25(self.g, self.origins, self.facilities, count=1)
        for key in ("baseline", "closures", "disrupted", "changes", "restorations",
                    "selection_method"):
            self.assertIn(key, result)

    def test_caller_supplied_closures_bypass_selection(self):
        manual = [{"id": "D1", "u": 1, "v": 2, "hypothetical": True}]
        result = analyze_25(self.g, self.origins, self.facilities,
                            closures=manual)
        self.assertEqual(result["selection_method"], "caller_supplied")
        self.assertEqual(len(result["closures"]), 1)

    def test_disruption_increases_or_disconnects(self):
        result = analyze_25(self.g, self.origins, self.facilities, count=1)
        for row in result["changes"]:
            if row["increase_m"] is not None:
                self.assertGreaterEqual(row["increase_m"], -1e-9)

    def test_restoration_never_worsens_reachable_origins(self):
        result = analyze_25(self.g, self.origins, self.facilities, count=1)
        for scenario in result["restorations"]:
            for old, new in zip(result["disrupted"], scenario["accessibility"]):
                if old["distance_m"] is not None:
                    self.assertIsNotNone(new["distance_m"])
                    self.assertLessEqual(new["distance_m"], old["distance_m"] + 1e-7)

    def test_exclude_pairs_flows_through(self):
        # First run to find selected pair, then exclude it; second run must differ
        r1 = analyze_25(self.g, self.origins, self.facilities, count=1)
        pair = [(r1["closures"][0]["u"], r1["closures"][0]["v"])]
        r2 = analyze_25(self.g, self.origins, self.facilities,
                        exclude_pairs=pair, count=1)
        self.assertNotEqual(
            tuple(sorted((r1["closures"][0]["u"], r1["closures"][0]["v"]))),
            tuple(sorted((r2["closures"][0]["u"], r2["closures"][0]["v"]))),
        )


# ---------------------------------------------------------------------------
# Real-data integration (skipped without cache)
# ---------------------------------------------------------------------------

@unittest.skipUnless(
    Path("data/heidelberg/manifest.json").exists(),
    "Real OSM cache not downloaded",
)
class OfflineRealData25Tests(unittest.TestCase):
    """Phase 2.5 integration tests using the verified Heidelberg OSM cache."""

    PHASE2_PAIRS = [
        (11247599, 11247600),   # C1 Vangerowstrasse
        (11247645, 645759168),  # C2 Iqbal-Ufer
        (13888159, 301109705),  # C3 Furtwanglerstrasse
    ]

    def test_phase25_offline_no_network(self):
        from lifelinetwin_geo.data import load, download
        from lifelinetwin_geo.analysis_25 import analyze_25
        with patch("requests.sessions.Session.request",
                   side_effect=AssertionError("Network forbidden")):
            self.assertIn("no network request", download("data/heidelberg"))
            graph, origins, facilities, manifest = load("data/heidelberg")
            result = analyze_25(
                graph, origins, facilities,
                exclude_pairs=self.PHASE2_PAIRS,
                count=3,
            )
            self.assertEqual(len(result["closures"]), 3)
            self.assertEqual(result["selection_method"],
                             "betweenness_baseline_used_nonadjacent")

    def test_phase25_closures_differ_from_phase2(self):
        from lifelinetwin_geo.data import load
        from lifelinetwin_geo.analysis_25 import analyze_25
        graph, origins, facilities, _ = load("data/heidelberg")
        result = analyze_25(
            graph, origins, facilities,
            exclude_pairs=self.PHASE2_PAIRS,
            count=3,
        )
        phase2_pairs = {tuple(sorted(p)) for p in self.PHASE2_PAIRS}
        for c in result["closures"]:
            self.assertNotIn(tuple(sorted((c["u"], c["v"]))), phase2_pairs)

    def test_phase25_deterministic(self):
        from lifelinetwin_geo.data import load
        from lifelinetwin_geo.analysis_25 import analyze_25
        graph, origins, facilities, _ = load("data/heidelberg")
        r1 = analyze_25(graph, origins, facilities,
                        exclude_pairs=self.PHASE2_PAIRS, count=3)
        r2 = analyze_25(graph, origins, facilities,
                        exclude_pairs=self.PHASE2_PAIRS, count=3)
        self.assertEqual(r1, r2)

    def test_phase25_route_distances_nonnegative_increase(self):
        from lifelinetwin_geo.data import load
        from lifelinetwin_geo.analysis_25 import analyze_25
        graph, origins, facilities, _ = load("data/heidelberg")
        result = analyze_25(graph, origins, facilities,
                            exclude_pairs=self.PHASE2_PAIRS, count=3)
        for row in result["changes"]:
            if row["increase_m"] is not None:
                self.assertGreaterEqual(row["increase_m"], -1e-7)

    def test_phase25_restoration_monotone(self):
        """Restoring a segment never worsens already-reachable origins."""
        from lifelinetwin_geo.data import load
        from lifelinetwin_geo.analysis_25 import analyze_25
        graph, origins, facilities, _ = load("data/heidelberg")
        result = analyze_25(graph, origins, facilities,
                            exclude_pairs=self.PHASE2_PAIRS, count=3)
        for scenario in result["restorations"]:
            for old, new in zip(result["disrupted"], scenario["accessibility"]):
                if old["distance_m"] is not None:
                    self.assertIsNotNone(new["distance_m"])
                    self.assertLessEqual(new["distance_m"],
                                        old["distance_m"] + 1e-7)

    def test_phase25_closures_used_by_baseline(self):
        """Every selected segment must have appeared in a baseline route."""
        from lifelinetwin_geo.data import load
        from lifelinetwin_geo.analysis_25 import analyze_25
        from lifelinetwin_geo.engine import accessibility
        graph, origins, facilities, _ = load("data/heidelberg")
        baseline = accessibility(graph, origins, facilities)
        used_pairs = set()
        for row in baseline:
            path = row.get("path", [])
            for a, b in zip(path, path[1:]):
                used_pairs.add(tuple(sorted((a, b))))
        result = analyze_25(graph, origins, facilities,
                            exclude_pairs=self.PHASE2_PAIRS, count=3)
        for c in result["closures"]:
            self.assertIn(tuple(sorted((c["u"], c["v"]))), used_pairs,
                          msg=f"Closure {c['id']} ({c['u']},{c['v']}) not in baseline routes")


if __name__ == "__main__":
    unittest.main()
