"""Export display geometry from the existing checksum-verified cache. No downloads."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    from lifelinetwin_geo.data import load
    graph, origins, facilities, manifest = load(ROOT / 'data/heidelberg')
    roads = []
    road_features = []
    edge_routes = {}
    seen = {}
    for u, v, data in graph.edges(data=True):
        geometry = data.get('geometry')
        coordinates = list(geometry.coords) if geometry is not None else [(graph.nodes[u]['x'], graph.nodes[u]['y']), (graph.nodes[v]['x'], graph.nodes[v]['y'])]
        line = [[round(x, 7), round(y, 7)] for x, y in coordinates]
        key = json.dumps(sorted((line, list(reversed(line)))))
        if key not in seen:
            seen[key] = len(roads)
            roads.append(line)
            kind = data.get('highway', 'unclassified')
            if isinstance(kind, list):
                kind = kind[0] if kind else 'unclassified'
            road_features.append({'u': u, 'v': v, 'kind': kind, 'coordinates': line})
        index = seen[key]
        displayed = roads[index]
        start = (float(graph.nodes[u]['x']), float(graph.nodes[u]['y']))
        squared = lambda coordinate: sum((a-b)**2 for a,b in zip(start,coordinate))
        reverse = squared(displayed[-1]) < squared(displayed[0])
        edge_key = f'{u}/{v}'
        length = float(data['length'])
        if edge_key not in edge_routes or length < edge_routes[edge_key]['length_m']:
            edge_routes[edge_key] = {'feature_index': index, 'reverse': reverse, 'length_m': length}
    result = {'manifest': manifest, 'roads': roads, 'origins': origins, 'facilities': facilities,
              'nodes': {str(n): [a['x'], a['y']] for n, a in graph.nodes(data=True)},
              'road_features': road_features, 'edge_routes': edge_routes}
    target = ROOT / 'frontend/public/data/heidelberg-atlas.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({'output': str(target), 'display_lines': len(roads), 'bytes': target.stat().st_size, 'downloaded': False}))

if __name__ == '__main__':
    main()
