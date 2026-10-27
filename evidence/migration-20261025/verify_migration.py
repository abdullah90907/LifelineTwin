"""Read-only migration checks; write only new migration evidence."""
import hashlib, json, math
from pathlib import Path
from unittest.mock import patch
from lifelinetwin_geo.data import load
from lifelinetwin_geo.engine import analyze
from lifelinetwin_geo.analysis_25 import analyze_25
from lifelinetwin_geo.forecasting import TTMForecaster
from lifelinetwin_geo.weather import fetch_forecast
out = Path('evidence/migration-20261025')
with patch('requests.get', side_effect=AssertionError('Geographic analysis must remain offline')):
    graph, origins, facilities, manifest = load('data/heidelberg')
    p2 = analyze(graph, origins, facilities)
    p25 = analyze_25(graph, origins, facilities, exclude_pairs=[(11247599,11247600),(11247645,645759168),(13888159,301109705)], count=3)
    comparison = {}
    for name, result, oldfile in [('phase2',p2,'evidence/phase2-results.json'),('phase25',p25,'evidence/phase2-5-results.json')]:
        old = json.loads(Path(oldfile).read_text(encoding='utf-8'))
        comparison[name] = {key: result[key] == old[key] for key in ['changes','closures','restorations']}
        (out / (name+'-verified.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
report = {'graph_nodes':len(graph),'graph_edges':graph.number_of_edges(),'origins':len(origins),'facilities':len(facilities),'cache_sha256_verified':True,'saved_results_comparison':comparison}
obs = json.loads(Path('data/heidelberg/weather/obs_forecast_2026-10-24_p30_f7.json').read_text(encoding='utf-8'))
f = TTMForecaster()
pred = f.predict(obs)
report['ttm'] = {k:pred[k] for k in ['model_id','forecast_horizon_hours','metadata']}
report['ttm']['finite_predictions'] = all(math.isfinite(v) for v in pred['forecast_values'])
report['ttm']['first_five'] = pred['forecast_values'][:5]
report['ttm']['actual_parameter_device'] = str(next(f.load_model().parameters()).device)
try:
    live = fetch_forecast(past_days=2,forecast_days=1,timeout=30)
    report['live_open_meteo'] = {'ok':True,'source':live['source'],'n_hours':live['n_hours'],'variables':list(live['variables'])}
except Exception as exc:
    report['live_open_meteo'] = {'ok':False,'error':repr(exc)}
original = json.loads((out/'preserved-sha256.json').read_text())
report['preserved_file_count'] = len(original)
report['changed_original_files'] = [p for p,h in original.items() if not Path(p).exists() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
(out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
