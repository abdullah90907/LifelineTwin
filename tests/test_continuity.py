import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import networkx as nx
from fastapi.testclient import TestClient

from lifelinetwin_backend.continuity import CaseRequest,calculate_case,render_brief
from lifelinetwin_backend.config import Settings
from lifelinetwin_backend.main import create_app

def fixture(region='houston'):
    graph=nx.MultiDiGraph()
    for u,v,length in [(1,2,100),(2,3,100),(1,4,500),(4,3,100)]:
        graph.add_edge(u,v,length=length);graph.add_edge(v,u,length=length)
    places=[{'id':'place/a','name':'Community A','node':1,'lat':29.7,'lon':-95.4,'source':'https://example.org/place/a'}]
    hospitals=[{'id':region+'/near','name':'Near hospital','node':2},{'id':region+'/far','name':'Alternative hospital','node':3}]
    return graph,places,hospitals,{'download_completed_utc':'2026-10-29T00:00:00Z','sha256':{'roads.graphml':'controlled-fixture'}}

def body(**overrides):
    return CaseRequest(**{'region':'houston','title':'Controlled outage exercise','source':'Explicit test exercise',
      'observed_at':'2026-10-28T00:00:00Z','unavailable_facilities':['houston/near'],**overrides})

class CalculationTests(unittest.TestCase):
    @patch('lifelinetwin_backend.continuity.dataset',side_effect=fixture)
    def test_outage_changes_access_and_restoration_recovers_it(self,_):
        result=calculate_case(body())
        self.assertEqual(result['communities'][0]['baseline_m'],100)
        self.assertEqual(result['communities'][0]['scenario_m'],200)
        self.assertEqual(result['communities'][0]['alternative_facility'],'Alternative hospital')
        self.assertEqual(result['summary']['communities_with_longer_routes'],1)
        self.assertEqual(result['alternatives'][0]['distance_saved_m'],100)
        self.assertIsNone(result['summary']['population_affected'])

    @patch('lifelinetwin_backend.continuity.dataset',side_effect=fixture)
    def test_no_remaining_facilities_and_temporary_proxy_do_not_fabricate_routes(self,_):
        result=calculate_case(body(unavailable_facilities=['houston/near','houston/far'],temporary_site='place/a'))
        self.assertIsNone(result['communities'][0]['scenario_m'])
        self.assertTrue(result['communities'][0]['newly_disconnected'])
        temporary=next(a for a in result['alternatives'] if a['kind']=='temporary_service')
        self.assertEqual(temporary['reconnected_communities'],1)
        self.assertIn('no hospital-equivalent',temporary['assumption'])

    @patch('lifelinetwin_backend.continuity.dataset',side_effect=fixture)
    def test_explicit_road_restriction_changes_paths_and_reopening_recovers_access(self,_):
        result=calculate_case(body(unavailable_facilities=[],closures=[{'id':'bridge','u':1,'v':2}]))
        self.assertEqual(result['communities'][0]['scenario_m'],600)
        self.assertNotEqual(result['communities'][0]['baseline_path'],result['communities'][0]['scenario_path'])
        self.assertEqual(result['alternatives'][0]['distance_saved_m'],500)

    @patch('lifelinetwin_backend.continuity.dataset',side_effect=fixture)
    def test_foreign_region_facilities_are_rejected(self,_):
        with self.assertRaisesRegex(ValueError,'does not belong'):
            calculate_case(body(unavailable_facilities=['alabama/near']))

    @patch('lifelinetwin_backend.continuity.dataset',side_effect=fixture)
    def test_road_selection_from_a_different_snapshot_is_rejected(self,_):
        with self.assertRaisesRegex(ValueError,'different geographic snapshot'):
            calculate_case(body(expected_graph_sha256='a'*64))

    def test_undocumented_specialty_records_are_not_emergency_alternatives(self):
        from lifelinetwin_backend.facility_scope import eligible_facilities
        chosen=eligible_facilities('alabama',[{'name':'Bryce Hospital'},{'name':'DCH Regional Medical Center'}])
        self.assertEqual([f['name'] for f in chosen],['DCH Regional Medical Center'])
        self.assertIn('live availability',chosen[0]['capability_status'])

    def test_duplicate_roads_and_future_sources_are_rejected(self):
        with self.assertRaises(ValueError): body(closures=[{'id':'a','u':1,'v':2},{'id':'b','u':2,'v':1}])
        with self.assertRaises(ValueError): body(observed_at='2099-01-01T00:00:00Z')

class PersistenceTests(unittest.TestCase):
    def test_attached_alert_is_preserved_as_context_without_changing_routes(self):
        feed={'alerts':{'status':'available','data':[{'id':'official-alert','headline':'Controlled warning'}],
                       'retrieved_at':'2026-10-28T00:00:00Z','source_url':'https://api.weather.gov/alerts/active'}}
        with tempfile.TemporaryDirectory() as directory,patch('lifelinetwin_backend.continuity.dataset',side_effect=fixture),patch('lifelinetwin_backend.continuity.signals',return_value=feed):
            settings=replace(Settings(),database_path=Path(directory)/'case.sqlite3')
            with TestClient(create_app(settings)) as client:
                response=client.post('/continuity/cases',json=body(context_alert='official-alert').model_dump(mode='json'))
                self.assertEqual(response.status_code,201)
                saved=response.json()
                self.assertEqual(saved['result']['summary']['largest_increase_m'],100)
                self.assertEqual(saved['request']['closures'],[])
                self.assertIn('does not establish',saved['result']['live_alert_context']['effect'])
                brief=client.get(f'/continuity/cases/{saved["id"]}/brief').text
                self.assertIn('Attached official alert context',brief)
                self.assertIn('Controlled warning',brief)

    def test_region_isolation_export_and_restart(self):
        with tempfile.TemporaryDirectory() as directory,patch('lifelinetwin_backend.continuity.dataset',side_effect=fixture):
            settings=replace(Settings(),database_path=Path(directory)/'case.sqlite3')
            with TestClient(create_app(settings)) as client:
                response=client.post('/continuity/cases',json=body().model_dump(mode='json'))
                self.assertEqual(response.status_code,201,response.text)
                record=response.json();identifier=record['id']
                self.assertEqual(client.get('/continuity/cases?region=alabama').json(),[])
                self.assertEqual(len(client.get('/continuity/cases?region=houston').json()),1)
                brief=client.get(f'/continuity/cases/{identifier}/brief')
                self.assertEqual(brief.status_code,200)
                self.assertIn('Affected population: unavailable.',brief.text)
                self.assertIn('attachment;',brief.headers['content-disposition'])
            with TestClient(create_app(settings)) as reopened:
                saved=reopened.get(f'/continuity/cases/{identifier}').json()
                self.assertEqual(saved,record)

    @patch('lifelinetwin_backend.continuity.signals',return_value={'alerts':{'status':'available','data':[]}})
    def test_invalid_alert_context_never_saves_a_case(self,_):
        with tempfile.TemporaryDirectory() as directory,patch('lifelinetwin_backend.continuity.dataset',side_effect=fixture):
            settings=replace(Settings(),database_path=Path(directory)/'case.sqlite3')
            with TestClient(create_app(settings)) as client:
                response=client.post('/continuity/cases',json=body(context_alert='foreign-or-expired-alert').model_dump(mode='json'))
                self.assertEqual(response.status_code,422)
                self.assertEqual(client.get('/continuity/cases?region=houston').json(),[])

if __name__=='__main__':unittest.main()
