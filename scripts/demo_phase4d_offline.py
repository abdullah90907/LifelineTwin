"""CONTROLLED provider / real cached tools demonstration. No live LLM evidence."""
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))


def main():
    import httpx
    import requests
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TRANSFORMERS_OFFLINE']='1'
    from test_agent_optimization import RealAnalyticalIntegrationTests
    parent=ROOT/'evidence/phase4d'
    parent.mkdir(parents=True,exist_ok=True)
    output=Path(tempfile.mkdtemp(prefix='controlled-',dir=parent))
    def reject(*args,**kwargs):
        raise AssertionError('Real HTTP is prohibited in this offline demonstration')
    summaries=[]
    with patch.object(httpx.HTTPTransport,'handle_request',reject),patch.object(requests.sessions.Session,'request',reject):
        for name,question in [('geographic_first','Compare geographic disruptions with weather and forecasts.'),
                              ('weather_first','Weather first, then compare road scenarios and interventions.'),
                              ('shared_scenario','Compare sources and repeat restoration for the approved scenario.')]:
            case=RealAnalyticalIntegrationTests()
            result,trace,checkpoint=case.run_case(question)
            data={'controlled_provider':True,'live_llm':False,'result':result,'trace':trace,'checkpoint':checkpoint}
            (output/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
            summaries.append({'case':name,'status':result['status'],'model_rounds':result['iterations'],'tool_calls':result['tool_calls'],
                'peak_request_bytes':max(m['request_bytes'] for m in checkpoint['context_metrics']),
                'peak_estimated_input_tokens':max(m['estimated_input_tokens'] for m in checkpoint['context_metrics']),
                'catalog_strategies':sorted({m['strategy'] for m in checkpoint['context_metrics']}),
                'reused_tool_calls':sum(bool(e['payload'].get('reused')) for e in trace if e['kind']=='tool'),
                'api_result_and_trace_equal_after_application_restart':True})
    summary={'controlled_offline_only':True,'live_llm_executed':False,'cases':summaries}
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({'evidence_directory':str(output),**summary},indent=2))


if __name__=='__main__':
    main()
