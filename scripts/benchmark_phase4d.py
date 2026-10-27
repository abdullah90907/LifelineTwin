"""Offline replay of recorded Phase 4C outputs; never calls an LLM or data API."""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from lifelinetwin_backend.agent import SYSTEM
    from lifelinetwin_backend.agent_tools import tool_definitions, model_view
    from lifelinetwin_backend.agent_context import context_messages, evidence_projection, request_metrics
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    source=ROOT/'evidence/phase4c-final/live-pj8ogqb2'
    trace=json.loads((source/'agent-trace-redacted.json').read_text())
    request=json.loads((source/'requests.json').read_text())['agent_request']
    incident=next(e['payload']['output'] for e in trace if e['kind']=='tool' and e['payload']['tool']=='retrieve_incident')
    initial=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({
        'question':request['question'],'incident_evidence_id':'E0','incident_untrusted':incident,
        'allowed_hypothetical_closures':request['allowed_closures'],
        'environment':{'mode':'cache','as_of':request['as_of'],'variable':'temperature_2m'}})}]
    old=list(initial); new=list(initial)
    evidence={'E0':{'category':'attributed_incident_claims','tool':'initial_incident_snapshot','data':incident}}
    rows=[]
    def capture(step):
        _,after=context_messages(new,evidence,tool_definitions(),model='openai/gpt-oss-20b',token_parameter='max_tokens')
        before=request_metrics(old,tool_definitions(),'openai/gpt-oss-20b','max_tokens')
        rows.append({'before_step':step,'old_history_bytes':before['request_bytes'],'managed_bytes':after['request_bytes'],
            'old_estimated_input_tokens':before['estimated_input_tokens'],'managed_estimated_input_tokens':after['estimated_input_tokens'],
            'strategy':after['strategy']})
    capture(1)
    for step,event in enumerate([e for e in trace if e['kind']=='tool'],2):
        e=event['payload']
        record={'category':e['category'],'tool':e['tool'],'data':e['output']}
        evidence[e['evidence_id']]=record
        assistant={'role':'assistant','content':None,'tool_calls':[{'id':e['call_id'],'type':'function',
            'function':{'name':e['tool'],'arguments':json.dumps(e['input'])}}]}
        old.append(assistant);new.append(assistant)
        for messages,view in ((old,model_view(e['output'])),(new,evidence_projection(record))):
            reply={'evidence_id':e['evidence_id'],'category':e['category'],'data':view,
                'note':'Cite original stored data using RFC6901 pointers, not this compressed view.'}
            encoded=json.dumps(reply)
            if len(encoded)>18000:
                encoded=json.dumps({'evidence_id':e['evidence_id'],'category':e['category'],'note':'Select a narrower source pointer'})
            messages.append({'role':'tool','tool_call_id':e['call_id'],'content':encoded})
        capture(step)
    result={'method':'Offline historical replay with current static schemas/system and compact serializer held equal; estimates are not provider token counts.',
        'live_provider_calls':0,'rows':rows,'final_byte_reduction_percent':round(100*(1-rows[-1]['managed_bytes']/rows[-1]['old_history_bytes']),2),
        'schema_bytes_current':len(json.dumps(tool_definitions()).encode()),'system_bytes_current':len(SYSTEM.encode())}
    path=args.output or ROOT/'evidence/phase4d'/('replay-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as handle:
        json.dump(result,handle,indent=2)
    print(json.dumps({'output':str(path),**result},indent=2))


if __name__=='__main__':
    main()
