"""Offline numeric audit and reconstruction of saved redacted live tool exchanges.

Never loads credentials, contacts a provider, or saves assembled request messages.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def audit():
    from lifelinetwin_backend.agent import SYSTEM
    from lifelinetwin_backend.agent_context import ContextPolicy, ContextLimit, context_messages, evidence_projection
    from lifelinetwin_backend.agent_schemas import AgentRequest
    from lifelinetwin_backend.agent_tools import tool_definitions
    source = ROOT / 'evidence/phase4c-final/live-aj_5_217'
    summary = json.loads((source / 'summary.json').read_text())
    trace = json.loads((source / 'agent-trace-redacted.json').read_text())
    request = AgentRequest.model_validate(json.loads((source / 'requests.json').read_text())['agent_request'])
    incident = next(e['payload']['output'] for e in trace if e['kind'] == 'tool')
    evidence = {'E0': {'category': 'attributed_incident_claims', 'tool': 'initial_incident_snapshot', 'data': incident}}
    messages = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': json.dumps({
        'question': request.question, 'incident_evidence_id': 'E0', 'incident_untrusted': incident,
        'allowed_hypothetical_closures': [c.model_dump() for c in request.allowed_closures],
        'environment': {'mode': request.mode, 'as_of': request.as_of.isoformat(), 'variable': request.variable}})}]
    rows = []

    def capture():
        row = {'before_step': len(rows) + 1}
        for label, policy in [('old', ContextPolicy(max_input_tokens=3500)), ('new', ContextPolicy())]:
            try:
                _, metrics = context_messages(messages, evidence, tool_definitions(), policy, 'openai/gpt-oss-20b', 'max_tokens')
                admitted = True
            except ContextLimit as exc:
                metrics, admitted = exc.metrics, False
            row[label] = {**metrics, 'admitted': admitted}
        rows.append(row)

    capture()
    note = ''
    for event in trace:
        payload = event['payload']
        if event['kind'] == 'decision':
            note = payload['assistant_note_untrusted']
        if event['kind'] != 'tool':
            continue
        eid = payload['evidence_id']
        if not payload.get('reused'):
            evidence[eid] = {'tool': payload['tool'], 'category': payload['category'], 'data': payload['output']}
        output = evidence[eid]['data']
        messages.append({'role': 'assistant', 'content': note or None, 'tool_calls': [{
            'id': payload['call_id'], 'type': 'function', 'function': {
                'name': payload['tool'], 'arguments': json.dumps(payload['input'])}}]})
        reply = {'evidence_id': eid, 'category': payload['category'], 'data': evidence_projection(evidence[eid]),
                 'note': 'Cite original stored data using RFC6901 pointers, not this compressed view.'}
        messages.append({'role': 'tool', 'tool_call_id': payload['call_id'], 'content': json.dumps(reply, allow_nan=False)})
        capture()
    samples = [{'estimated_input': r['estimated_input_tokens'], 'reported_input': r['reported_usage']['input_tokens'],
                'overestimate_tokens': r['estimated_input_tokens'] - r['reported_usage']['input_tokens'],
                'ratio': r['estimated_input_tokens'] / r['reported_usage']['input_tokens']}
               for r in summary['usage_records']]
    return {'live_requests': 0, 'source': str(source.relative_to(ROOT)), 'usage_samples': samples,
            'replay': rows, 'note': 'Reconstructed from redacted decisions/tools; not stored raw wire payloads. No token count exists for the unsent step.'}


if __name__ == '__main__':
    result = audit()
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({'output': str(target), 'replay': [{'step': r['before_step'], 'old': r['old']['admitted'],
        'new': r['new']['admitted'], 'new_estimate': r['new']['estimated_input_tokens']} for r in result['replay']]}))
