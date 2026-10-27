"""Phase 4D offline contracts and realistic real-tool/controlled-provider tests."""
import copy
import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from lifelinetwin_backend.agent_context import (ContextPolicy,ContextLimit,UsageWindow,context_messages,
    evidence_projection,packed,request_metrics,fits)
from lifelinetwin_backend.agent_tools import inspect_selection,pointer_value,tool_definitions,REGISTRY
from lifelinetwin_backend.agent_provider import ProviderConfig,ProviderConfigurationError,OpenAICompatibleProvider
from lifelinetwin_backend.agent_failures import ProviderFailure
from lifelinetwin_backend.agent_storage import AgentRunRow
from lifelinetwin_backend.config import Settings,ROOT
from lifelinetwin_backend.main import create_app
from _phase4d_fixtures import AdaptiveEvidenceProvider


class ContextContractTests(unittest.TestCase):
    def evidence(self):
        return {"E0":{"category":"attributed_incident_claims","tool":"initial_incident_snapshot", "data":{"kind":"hypothetical","description":"untrusted "*2000}}}

    def messages(self,evidence):
        return [{"role":"system","content":"Trusted policy"},{"role":"user","content":json.dumps({"question":"Investigate access","incident_untrusted":evidence['E0']['data']})}]

    def test_long_raw_incident_is_not_repeated_and_question_survives(self):
        evidence=self.evidence(); original=copy.deepcopy(evidence)
        messages,metrics=context_messages(self.messages(evidence),evidence,tool_definitions())
        self.assertTrue(fits(metrics))
        self.assertEqual(json.loads(messages[1]["content"])["question"],"Investigate access")
        self.assertLess(metrics["request_bytes"],metrics["unmanaged_request_bytes"])
        self.assertEqual(evidence,original)

    def test_atomic_recent_exchange_and_archives_have_no_orphan_tools(self):
        evidence=self.evidence(); messages=self.messages(evidence)
        for n in range(8):
            messages.extend([{"role":"assistant","content":None,"tool_calls":[{"id":str(n),"type":"function","function":{"name":"retrieve_incident","arguments":"{}"}}]},
                             {"role":"tool","tool_call_id":str(n),"content":json.dumps({"evidence_id":"E0","data":"x"*1000})}])
        managed,metrics=context_messages(messages,evidence,tool_definitions())
        self.assertEqual(sum(m["role"]=="assistant" for m in managed),8)
        active=set()
        for message in managed:
            if message["role"]=="assistant":
                active={c["id"] for c in message.get("tool_calls",[])}
            elif message["role"]=="tool":
                self.assertIn(message["tool_call_id"],active)
        self.assertGreater(metrics["archived_exchanges"],0)
        self.assertTrue(fits(metrics))

    def test_minimum_context_rejected_without_dropping_goal(self):
        evidence=self.evidence()
        messages=self.messages(evidence)
        messages[1]["content"]=json.dumps({"question":"full question "*2000,"incident_untrusted":evidence['E0']['data']})
        with self.assertRaises(ContextLimit):
            context_messages(messages,evidence,tool_definitions(),ContextPolicy(max_input_tokens=1024,max_request_bytes=4096))

    def test_provider_guard_rejects_oversize_before_sdk_construction(self):
        from pydantic import SecretStr
        provider=OpenAICompatibleProvider(ProviderConfig("configured","https://no.invalid/v1",SecretStr("test-only"),max_input_tokens=1024))
        with patch("openai.OpenAI") as sdk:
            with self.assertRaises(ProviderFailure) as failure:
                provider.complete([{"role":"user","content":"x"*30000}],tool_definitions(),1)
            self.assertEqual(failure.exception.metadata.category,"context_budget")
            sdk.assert_not_called()

    def test_request_byte_measurement_and_estimate_are_labeled(self):
        metrics=request_metrics([{"role":"user","content":"hello"}],[],"model","max_tokens")
        body={"model":"model","messages":[{"role":"user","content":"hello"}],"tools":[],"tool_choice":"auto","max_tokens":1800}
        self.assertEqual(metrics["request_bytes"],len(packed(body).encode()))
        self.assertIn("estimate",metrics["token_count_method"])

    def test_rate_window_charges_success_and_retains_failed_reservation(self):
        meter=UsageWindow(6000)
        failed=meter.reserve(4000,0)
        self.assertEqual(meter.wait_required(3000,10),50)
        self.assertEqual(meter.wait_required(3000,60),0)
        meter.reconcile(failed,{"total_tokens":2000})
        self.assertEqual(meter.wait_required(3000,10),0)
        self.assertEqual(meter.wait_required(7000,60),float('inf'))

    def test_paged_arrays_text_and_escaped_pointers_preserve_full_source(self):
        data={"numbers":list(range(100)),"text":"abcdefghijklmnopqrstuvwxyz"*80,"a/b":{"~x":42}}
        evidence={"E1":{"data":data,"category":"test","tool":"test"}}
        page=inspect_selection({"evidence_id":"E1","pointer":"/numbers","offset":32,"limit":4},evidence)
        self.assertEqual([r['value'] for r in page['items']],[32,33,34,35])
        self.assertEqual(page['next_offset'],36)
        self.assertEqual(pointer_value(data,page['items'][0]['pointer']),32)
        excerpt=inspect_selection({"evidence_id":"E1","pointer":"/text","text_offset":500,"text_limit":100},evidence)
        self.assertEqual(excerpt['text_excerpt'],data['text'][500:600])
        scalar=inspect_selection({"evidence_id":"E1","pointer":"/a~1b/~0x"},evidence)
        self.assertEqual(scalar['value'],42)
        self.assertEqual(len(data['numbers']),100)

    def test_large_objects_and_items_expose_drilldown_without_replacing_evidence(self):
        data={"items":[{"large":"x"*6000,"number":12.5}],"obj":{str(i):"x"*100 for i in range(60)}}
        evidence={"E1":{"data":data,"category":"test","tool":"test"}}
        page=inspect_selection({"evidence_id":"E1","pointer":"/items"},evidence)
        self.assertTrue(page['items'][0]['value']['detail_available'])
        detail=inspect_selection({"evidence_id":"E1","pointer":"/items/0/number"},evidence)
        self.assertEqual(detail['value'],12.5)
        keys=inspect_selection({"evidence_id":"E1","pointer":"/obj","limit":3},evidence)
        self.assertEqual(keys['keys'],['0','1','2'])
        self.assertEqual(keys['next_offset'],3)

    def test_compact_schemas_keep_validation_and_all_tool_choices(self):
        definitions=tool_definitions()
        self.assertEqual({d['function']['name'] for d in definitions},set(REGISTRY))
        self.assertNotIn('"title":',json.dumps(definitions))
        for definition in definitions:
            self.assertFalse(definition['function']['parameters']['additionalProperties'])

    def test_latest_inspection_is_never_silently_archived_when_it_cannot_fit(self):
        evidence=self.evidence(); messages=self.messages(evidence)
        messages.extend([{'role':'assistant','content':None,'tool_calls':[{'id':'inspect','type':'function','function':{'name':'inspect_evidence','arguments':'{}'}}]},
                         {'role':'tool','tool_call_id':'inspect','content':json.dumps({'data':'x'*30000})}])
        with self.assertRaises(ContextLimit):
            context_messages(messages,evidence,tool_definitions())

    def test_config_limits_validate_without_reading_or_changing_provider(self):
        env={'LIFELINETWIN_LLM_MODEL':'configured','LIFELINETWIN_LLM_BASE_URL':'https://no-network.invalid/v1','LIFELINETWIN_LLM_API_KEY':'test-only',
             'LIFELINETWIN_LLM_TOKENS_PER_MINUTE':'8000','LIFELINETWIN_LLM_MAX_RATE_WAIT_SECONDS':'30'}
        with patch.dict(os.environ,env,clear=True):
            config=ProviderConfig.from_environment()
            self.assertEqual(config.tokens_per_minute,8000)
            self.assertEqual(config.max_rate_wait_seconds,30)
            self.assertEqual(config.model,'configured')
            os.environ['LIFELINETWIN_LLM_MAX_INPUT_TOKENS']='not-an-integer'
            with self.assertRaises(ProviderConfigurationError):
                ProviderConfig.from_environment()

    def test_local_context_and_rate_admission_do_not_contact_provider(self):
        from test_agent_reliability import RunnerReliabilityTests,response
        for policy,category in [(ContextPolicy(1024,4096),'context_budget'),(ContextPolicy(tokens_per_minute=1024),'rate_budget')]:
            harness=RunnerReliabilityTests(); harness.setUp()
            try:
                harness.provider.context_policy=policy
                result,provider,analytical,_=harness.run_case([response()])
                self.assertEqual(result.status,'limited')
                self.assertEqual(provider.call_count,0)
                self.assertEqual(analytical.call_count,0)
                failure=next(t['payload'] for t in harness.trace if t['kind']=='provider_failure')
                self.assertEqual(failure['category'],category)
                self.assertIsNone(failure['http_status'])
            finally:
                harness.tearDown()

    def test_usage_metadata_is_numeric_and_output_reservation_configurable(self):
        from pydantic import SecretStr
        provider=OpenAICompatibleProvider(ProviderConfig('configured','https://no-network.invalid/v1',SecretStr('test-only'),output_tokens=512))
        completed=SimpleNamespace(model='configured',_request_id='req_offline_usage',choices=[SimpleNamespace(message=SimpleNamespace(content=None,tool_calls=[]))],
                                  usage=SimpleNamespace(prompt_tokens=1234,completion_tokens=200,total_tokens=1434))
        with patch('openai.OpenAI') as sdk:
            sdk.return_value.__enter__.return_value.chat.completions.create.return_value=completed
            result=provider.complete([{'role':'user','content':'test'}],tool_definitions(),1)
        self.assertEqual(result['usage'],{'input_tokens':1234,'output_tokens':200,'total_tokens':1434})
        self.assertEqual(sdk.return_value.__enter__.return_value.chat.completions.create.call_args.kwargs['max_completion_tokens'],512)


class RealAnalyticalIntegrationTests(unittest.TestCase):
    def run_case(self,question,provider_factory=AdaptiveEvidenceProvider,max_iterations=8):
        with tempfile.TemporaryDirectory() as folder:
            settings=replace(Settings(),database_path=Path(folder)/'test.sqlite3')
            saved_scenario=json.loads((ROOT/'evidence/phase2-5-results.json').read_text(encoding='utf-8'))
            approved=[{k:c[k] for k in ('id','u','v')} for c in saved_scenario['closures']]
            request={'question':question,'as_of':'2026-10-24T19:55:49Z','allowed_closures':approved,'max_iterations':max_iterations,'max_tool_calls':16,'timeout_seconds':240,'tool_timeout_seconds':60}
            app=create_app(settings,agent_provider_factory=provider_factory)
            with TestClient(app) as client:
                incident=client.post('/incidents',json={'title':'Offline Heidelberg hypothetical investigation','description':'Controlled provider test; actual cached data only.','kind':'hypothetical','occurred_at':'2026-10-24T19:55:49Z'}).json()
                response=client.post(f"/incidents/{incident['id']}/agent-investigations",json=request)
                self.assertEqual(response.status_code,201,response.text)
                saved=response.json()
                self.assertEqual(saved['status'],'completed',saved)
                trace=client.get(f"/agent-investigations/{saved['id']}/trace").json()
                with app.state.database.sessions() as session:
                    checkpoint=session.get(AgentRunRow,saved['id']).checkpoint
                for finding in saved['result']['findings']:
                    citation=finding['citation']
                    self.assertEqual(finding['value'],pointer_value(checkpoint['evidence'][citation['evidence_id']]['data'],citation['pointer']))
                for metric in checkpoint['context_metrics']:
                    self.assertTrue(fits(metric))
                self.assertFalse(saved['model_identity']['live_llm'])
                self.assertTrue(any(t['payload'].get('tool')=='inspect_evidence' for t in trace))
                self.assertTrue(any(f['evidence_category']=='pretrained_prediction' for f in saved['result']['findings']))
                best=next(f['value'] for f in saved['result']['findings'] if isinstance(f['value'],dict) and 'osm_segments' in f['value'])
                self.assertGreater(best['distance_saved_m_for_already_reachable'],0)
                self.assertEqual(len(best['osm_segments']),2)
                self.assertTrue(all(r['human_review_required'] for r in saved['result']['recommendations']))
            with TestClient(create_app(settings,agent_provider_factory=AdaptiveEvidenceProvider)) as client:
                self.assertEqual(client.get(f"/agent-investigations/{saved['id']}").json(),saved)
                self.assertEqual(client.get(f"/agent-investigations/{saved['id']}/trace").json(),trace)
            return saved,trace,checkpoint

    def test_real_geo_weather_forecast_and_evidence_dependent_followup(self):
        saved,trace,checkpoint=self.run_case('Compare approved geographic disruptions with environmental evidence and forecast.')
        self.assertEqual(saved['iterations'],3)
        self.assertGreaterEqual(saved['tool_calls'],6)

    def test_different_weather_first_investigation_order(self):
        saved,trace,checkpoint=self.run_case('Weather first, then evaluate the approved road scenario and interventions.')
        first=next(t['payload']['selected_tools'] for t in trace if t['kind']=='decision')
        self.assertEqual(first,['retrieve_observations','generate_forecast'])
        self.assertEqual(saved['iterations'],4)

    def test_overlapping_geo_tools_share_real_scenario_evidence(self):
        saved,trace,checkpoint=self.run_case('Compare all sources and repeat restoration using the same approved scenario.')
        compared=next(t['payload'] for t in trace if t['kind']=='tool' and t['payload']['tool']=='compare_restorations')
        analyzed=next(t['payload'] for t in trace if t['kind']=='tool' and t['payload']['tool']=='analyze_closures')
        self.assertTrue(compared['reused'])
        self.assertIsNone(compared['output'])
        self.assertEqual(compared['evidence_id'],analyzed['evidence_id'])


if __name__=='__main__':
    unittest.main()
