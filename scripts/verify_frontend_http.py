"""Read-only local frontend/proxy smoke test. Never invokes inference or an agent."""
import json
from pathlib import Path
from urllib.request import urlopen
ROOT = Path(__file__).resolve().parents[1]

def main():
    rows = []
    values = {}
    for path in ['/', '/atlas', '/incidents', '/intelligence', '/api/health', '/api/analysis/baseline',
                 '/api/incidents?limit=12&offset=0', '/api/openapi.json', '/data/heidelberg-atlas.json']:
        with urlopen('http://127.0.0.1:5173' + path, timeout=30) as response:
            body = response.read()
            rows.append({'path': path, 'status': response.status, 'bytes': len(body)})
            assert response.status == 200
            if path.startswith('/api/') or path.startswith('/data/'):
                values[path] = json.loads(body)
            else:
                assert b'root' in body and b'LifelineTwin' in body
    health = values['/api/health']
    baseline = values['/api/analysis/baseline']['analysis']['baseline']
    reachable = [r['distance_m'] for r in baseline if r['distance_m'] is not None]
    atlas = values['/data/heidelberg-atlas.json']
    manifest = json.loads((ROOT / 'data/heidelberg/manifest.json').read_text())
    assert atlas['manifest'] == manifest
    assert values['/api/analysis/baseline']['dataset'] == manifest
    assert health['status'] == 'ok'
    output = {'checks': rows, 'health': health, 'incident_count_in_first_page': len(values['/api/incidents?limit=12&offset=0']),
              'reachable_origins': len(reachable), 'total_origins': len(baseline), 'mean_distance_m': sum(reachable) / len(reachable),
              'display_road_lines': len(atlas['roads']), 'display_bytes': len(json.dumps(atlas).encode()),
              'static_and_api_manifest_match': True, 'agent_requests': 0, 'forecast_requests': 0, 'write_requests': 0}
    target = ROOT / 'evidence/phase5a/http-smoke.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    main()
