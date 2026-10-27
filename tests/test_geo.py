"""Tiny SYNTHETIC graphs validate algorithms, not real geographic coverage."""
import unittest
from unittest.mock import patch
from pathlib import Path
import networkx as nx
from lifelinetwin_geo.engine import accessibility, close_segments, analyze, compare


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.g = nx.MultiDiGraph()
        self.g.add_edge(1, 2, length=10)
        self.g.add_edge(1, 2, length=50)
        self.g.add_edge(2, 3, length=20)
        self.g.add_edge(1, 3, length=80)
        self.g.add_node(4)
        self.origins = [{"id": "a", "node": 1}, {"id": "b", "node": 4}]
        self.facilities = [{"node": 3}]

    def test_shortest_parallel_edge_and_unreachable(self):
        rows = accessibility(self.g, self.origins, self.facilities)
        self.assertEqual(rows[0]['distance_m'], 30)
        self.assertEqual(rows[0]['path'], [1, 2, 3])
        self.assertIsNone(rows[1]['distance_m'])

    def test_direction_is_preserved(self):
        rows = accessibility(self.g, [{"id": "a", "node": 3}], [{"node": 1}])
        self.assertIsNone(rows[0]['distance_m'])

    def test_nearest_of_multiple_facilities(self):
        row = accessibility(self.g, self.origins, [{"node": 2}, {"node": 3}])[0]
        self.assertEqual(row['distance_m'], 10)
        self.assertEqual(row['facility_node'], 2)

    def test_closes_both_directions_all_parallel_without_mutation(self):
        self.g.add_edge(2, 1, length=10)
        closed = close_segments(self.g, [{"u": 1, "v": 2}])
        self.assertFalse(closed.has_edge(1, 2))
        self.assertFalse(closed.has_edge(2, 1))
        self.assertEqual(self.g.number_of_edges(), 5)
        self.assertEqual(accessibility(closed, self.origins, self.facilities)[0]['distance_m'], 80)

    def test_reconnection_and_independent_restoration(self):
        closures = [{"id": "C1", "u": 1, "v": 2}, {"id": "C2", "u": 1, "v": 3}]
        result = analyze(self.g, self.origins, self.facilities, closures)
        self.assertTrue(result['changes'][0]['newly_disconnected'])
        self.assertFalse(result['changes'][1]['newly_disconnected'])
        self.assertEqual([r['reconnected_origins'] for r in result['restorations']], [1, 1])
        distances = {r['reopened']: r['accessibility'][0]['distance_m'] for r in result['restorations']}
        self.assertEqual(distances, {'C1': 30, 'C2': 80})
        self.assertEqual(self.g.number_of_edges(), 4)

    def test_distance_savings_rank(self):
        self.g.add_edge(1, 3, length=100, key=9)
        self.g.add_edge(1, 5, length=100)
        self.g.add_edge(5, 3, length=100)
        result = analyze(self.g, self.origins, self.facilities,
                         [{"id": "C1", "u": 1, "v": 2}, {"id": "C2", "u": 1, "v": 3}])
        self.assertEqual(result['restorations'][0]['reopened'], 'C1')
        self.assertEqual(result['restorations'][0]['distance_saved_m_for_already_reachable'], 170)

    def test_invalid_weights_rejected(self):
        for weight in (None, -1, float('nan'), float('inf'), '10'):
            with self.subTest(weight=weight):
                self.g[1][2][0]['length'] = weight
                with self.assertRaises(ValueError):
                    accessibility(self.g, self.origins, self.facilities)

    def test_missing_facility_rejected(self):
        with self.assertRaises(ValueError):
            accessibility(self.g, self.origins, [])
        with self.assertRaises(ValueError):
            accessibility(self.g, self.origins, [{'node': 999}])

    def test_origin_at_hospital(self):
        self.assertEqual(accessibility(self.g, [{'id': 'a', 'node': 3}], self.facilities)[0]['distance_m'], 0)

    def test_reconnection_has_priority_over_distance_savings(self):
        graph = nx.MultiDiGraph()
        graph.add_weighted_edges_from([(1, 9, 10), (4, 9, 10), (4, 5, 100), (5, 9, 100)], weight='length')
        result = analyze(graph, [{'id': 'a', 'node': 1}, {'id': 'b', 'node': 4}], [{'node': 9}],
                         [{'id': 'C1', 'u': 1, 'v': 9}, {'id': 'C2', 'u': 4, 'v': 9}])
        self.assertEqual(result['restorations'][0]['reopened'], 'C1')
        self.assertEqual(result['restorations'][0]['reconnected_origins'], 1)
        self.assertEqual(result['restorations'][1]['distance_saved_m_for_already_reachable'], 190)

    def test_distance_change(self):
        original = accessibility(self.g, self.origins, self.facilities)
        closed = accessibility(close_segments(self.g, [{'u': 1, 'v': 2}]), self.origins, self.facilities)
        self.assertEqual(compare(original, closed)[0]['increase_m'], 50)


@unittest.skipUnless(Path('data/heidelberg/manifest.json').exists(), 'Real OSM cache not downloaded')
class OfflineRealDataTests(unittest.TestCase):
    def test_offline_repeatable_and_monotonic(self):
        from lifelinetwin_geo.data import load, download
        # Any HTTP request makes this test fail, including unnoticed cache misses.
        with patch('requests.sessions.Session.request', side_effect=AssertionError('Network forbidden')):
            self.assertIn('no network request', download('data/heidelberg'))
            graph, origins, facilities, manifest = load('data/heidelberg')
            self.assertGreaterEqual(len(facilities), 2)
            self.assertGreaterEqual(len(origins), 5)
            self.assertLessEqual(len(origins), 10)
            result = analyze(graph, origins, facilities)
            self.assertEqual(result, analyze(graph, origins, facilities))
            self.assertEqual(len(result['closures']), 3)
            for row in result['changes']:
                if row['increase_m'] is not None:
                    self.assertGreaterEqual(row['increase_m'], -1e-7)
            for scenario in result['restorations']:
                for old, new in zip(result['disrupted'], scenario['accessibility']):
                    if old['distance_m'] is not None:
                        self.assertIsNotNone(new['distance_m'])
                        self.assertLessEqual(new['distance_m'], old['distance_m'] + 1e-7)


if __name__ == '__main__':
    unittest.main()
