"""Region-isolated, evidence-led continuity cases and reproducible comparisons."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from threading import Lock
import time
from pathlib import Path
from typing import Literal

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict, model_validator
from sqlalchemy import select

from .config import ROOT
from .database import ContinuityCaseRow

PILOTS={
 'houston':{'name':'Houston, Texas','focus':'Texas Medical Center continuity','latitude':29.7075,'longitude':-95.395,'bbox':[-95.43,29.68,-95.36,29.735]},
 'alabama':{'name':'West Alabama','focus':'Tuscaloosa–Northport–Moundville care access','latitude':33.17,'longitude':-87.58,'bbox':[-87.71,32.97,-87.46,33.29]},
}
_dataset_lock=Lock()

def pilot(region):
    if region not in PILOTS: raise ValueError('Unknown region')
    return PILOTS[region]

@lru_cache(maxsize=8)
def _signals(region,bucket):
    location=pilot(region)
    def fetch(kind):
        url='https://api.weather.gov/alerts/active' if kind=='alerts' else 'https://api.open-meteo.com/v1/forecast'
        params={'point':f'{location["latitude"]},{location["longitude"]}'} if kind=='alerts' else {
          'latitude':location['latitude'],'longitude':location['longitude'],'timezone':'GMT',
          'current':'temperature_2m,precipitation,wind_speed_10m','forecast_days':1}
        try:
            response=requests.get(url,params=params,headers={'User-Agent':'LifelineTwin (https://github.com/abdullah90907/LifelineTwin)'},timeout=(5,20))
            response.raise_for_status();payload=response.json()
            if kind=='alerts':
                if not isinstance(payload.get('features'),list): raise ValueError('Missing alert data')
                data=[{key:f.get('properties',{}).get(key) for key in ('id','event','severity','headline','description','instruction','onset','expires','areaDesc')} for f in payload['features']]
            else:
                if not payload.get('current',{}).get('time'): raise ValueError('Missing weather data')
                data={'current':payload['current'],'units':payload.get('current_units',{})}
            return {'status':'available','source_url':response.url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'data':data}
        except (requests.RequestException,ValueError,KeyError):
            return {'status':'unavailable','source_url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'data':None}
    with ThreadPoolExecutor(max_workers=2) as pool:
        alerts,weather=list(pool.map(fetch,('alerts','weather')))
    return {'region':region,'alerts':alerts,'weather':weather,'coverage':'Weather and alerts cover the regional reference point, not every community. Cached up to five minutes.'}

def signals(region):
    pilot(region)
    return _signals(region,int(time.monotonic()//300))

@lru_cache(maxsize=4)
def _dataset(region,signature):
    from lifelinetwin_geo.data import load
    from .facility_scope import eligible_facilities
    graph,origins,facilities,manifest=load(ROOT/f'data/{region}')
    facilities=eligible_facilities(region,facilities)
    if len(facilities)<2: raise ValueError('Two documented emergency-service facilities are required')
    community_file=ROOT/f'data/{region}/communities.json'
    if community_file.exists():
        communities=json.loads(community_file.read_text(encoding='utf-8'))
    else: communities=[o for o in origins if o.get('name')]
    if not communities: raise ValueError('Named community data has not been validated for this region')
    return graph,communities,facilities,manifest

def dataset(region):
    pilot(region)
    folder=ROOT/f'data/{region}'
    files=[folder/name for name in ('manifest.json','roads.graphml','origins.json','facilities.json','hospitals.geojson')]
    if (folder/'communities.json').exists(): files.append(folder/'communities.json')
    signature=tuple((p.stat().st_size,p.stat().st_mtime_ns) for p in files)
    with _dataset_lock:
        return _dataset(region,signature)

class Road(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(min_length=1,max_length=100)
    u:int
    v:int

class CaseRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    region:Literal['houston','alabama']
    title:str=Field(min_length=3,max_length=180)
    evidence_kind:Literal['exercise','user_reported']='exercise'
    source:str=Field(min_length=5,max_length=1000)
    observed_at:AwareDatetime
    unavailable_facilities:list[str]=Field(default_factory=list,max_length=30)
    closures:list[Road]=Field(default_factory=list,max_length=6)
    temporary_site:str|None=None
    context_alert:str|None=Field(default=None,max_length=1000)
    expected_graph_sha256:str|None=Field(default=None,min_length=64,max_length=64)

    @model_validator(mode='after')
    def validate_case(self):
        if not self.unavailable_facilities and not self.closures: raise ValueError('Choose a facility outage or a road restriction')
        if len(set(self.unavailable_facilities))!=len(self.unavailable_facilities): raise ValueError('Duplicate facility')
        if len({tuple(sorted((r.u,r.v))) for r in self.closures})!=len(self.closures): raise ValueError('Duplicate road segment')
        if self.observed_at>datetime.now(timezone.utc): raise ValueError('Observation time cannot be in the future')
        return self

def routes(graph,communities,facilities):
    from lifelinetwin_geo.engine import accessibility
    if facilities: return accessibility(graph,communities,facilities)
    return [{'id':o['id'],'node':o['node'],'distance_m':None,'facility_node':None,'path':[]} for o in communities]

def benefit(before,after):
    reconnected=sum(a['distance_m'] is None and b['distance_m'] is not None for a,b in zip(before,after,strict=True))
    saved=sum(max(0,a['distance_m']-b['distance_m']) for a,b in zip(before,after,strict=True) if a['distance_m'] is not None and b['distance_m'] is not None)
    shorter=sum(a['distance_m'] is not None and b['distance_m'] is not None and a['distance_m']-b['distance_m']>1e-6 for a,b in zip(before,after,strict=True))
    return {'reconnected_communities':reconnected,'communities_with_shorter_routes':shorter,'distance_saved_m':saved,'mean_distance_saved_m':saved/shorter if shorter else 0}

def calculate_case(body:CaseRequest):
    from lifelinetwin_geo.engine import close_segments
    graph,communities,facilities,manifest=dataset(body.region)
    if body.expected_graph_sha256 and body.expected_graph_sha256!=manifest['sha256']['roads.graphml']:
        raise ValueError('Road selection belongs to a different geographic snapshot')
    known={f['id'] for f in facilities}
    if not set(body.unavailable_facilities)<=known: raise ValueError('Facility does not belong to this region')
    if body.temporary_site and body.temporary_site not in {o['id'] for o in communities}: raise ValueError('Unknown temporary-site community')
    closures=[r.model_dump() for r in body.closures]
    remaining=[f for f in facilities if f['id'] not in body.unavailable_facilities]
    disrupted_graph=close_segments(graph,closures) if closures else graph
    baseline=routes(graph,communities,facilities)
    after=routes(disrupted_graph,communities,remaining)
    facility_by_node={f['node']:f['name'] for f in remaining}
    rows=[]
    for community,b,a in zip(communities,baseline,after,strict=True):
        rows.append({'id':community['id'],'name':community['name'],'source':community.get('source'),
          'baseline_m':b['distance_m'],'scenario_m':a['distance_m'],
          'increase_m':a['distance_m']-b['distance_m'] if a['distance_m'] is not None and b['distance_m'] is not None else None,
          'newly_disconnected':b['distance_m'] is not None and a['distance_m'] is None,
          'alternative_facility':facility_by_node.get(a['facility_node']),
          'baseline_path':b['path'],'scenario_path':a['path'],
          'reference_point':{'latitude':community['lat'],'longitude':community['lon']},'population_affected':None})
    alternatives=[]
    for facility in facilities:
        if facility['id'] not in body.unavailable_facilities: continue
        comparison=routes(disrupted_graph,communities,remaining+[facility])
        alternatives.append({'id':'facility:'+facility['id'],'action':f'Restore availability of {facility["name"]}',
          'kind':'facility_restoration',**benefit(after,comparison),'assumption':'Requires operator verification of staffing, service capability, and feasibility.'})
    for closure in closures:
        restored=close_segments(graph,[r for r in closures if r['id']!=closure['id']])
        comparison=routes(restored,communities,remaining)
        alternatives.append({'id':'road:'+closure['id'],'action':f'Reopen road segment {closure["id"]}',
          'kind':'road_restoration',**benefit(after,comparison),'assumption':'All other restrictions and facility assumptions remain in force.'})
    if body.temporary_site:
        place=next(o for o in communities if o['id']==body.temporary_site)
        comparison=routes(disrupted_graph,communities,remaining+[{'node':place['node']}])
        alternatives.append({'id':'temporary:'+place['id'],'action':f'Explore a temporary service point at {place["name"]}',
          'kind':'temporary_service',**benefit(after,comparison),'assumption':'Location-only access proxy; no hospital-equivalent service, capacity, land access, staffing, or deployment feasibility is established.'})
    alternatives.sort(key=lambda a:(-a['reconnected_communities'],-a['distance_saved_m'],a['id']))
    snapshot=hashlib.sha256(json.dumps(body.model_dump(mode='json'),sort_keys=True).encode()).hexdigest()
    return {'region':body.region,'region_name':PILOTS[body.region]['name'],'computed_at':datetime.now(timezone.utc).isoformat(),
      'evidence_kind':body.evidence_kind,'verification':'exercise' if body.evidence_kind=='exercise' else 'user report; not independently verified',
      'input_sha256':snapshot,'dataset':manifest,'source':body.source,'observed_at':body.observed_at.isoformat(),
      'facility_scope':facilities,
      'summary':{'communities_evaluated':len(rows),'communities_with_longer_routes':sum((r['increase_m'] or 0)>1e-6 for r in rows),
        'communities_newly_disconnected':sum(r['newly_disconnected'] for r in rows),
        'largest_increase_m':max([r['increase_m'] or 0 for r in rows],default=0),'population_affected':None},
      'communities':rows,'alternatives':alternatives,
      'limitations':['Community reference points represent locations, not every resident or a population-weighted catchment.',
        'Population impact is unavailable; no affected-person count is inferred from reference points.',
        'Only the explicitly documented emergency-service subset is compared; operator websites document services, not current availability, capacity or suitability for a particular patient.',
        'Distances exclude travel-time, traffic, and snap offsets; hospitals and roads outside the bounded snapshot are excluded.',
        'The observation time records the case source; the calculation uses the downloaded snapshot and does not reconstruct historical conditions.',
        'Live weather warnings do not automatically close roads. Facility outages and road restrictions are explicit case inputs.',
        'Interventions are independently modeled comparisons, not operational instructions.']}

def render_brief(record):
    result=record['result']; request=record['request']; summary=result['summary']
    lines=[f'# {request["title"]}',f'Region: {result["region_name"]}',f'Case: {record["id"]}',
      f'Evidence status: {result["verification"]}',f'Source: {request["source"]}',f'Observed: {request["observed_at"]}',
      f'Computed: {result["computed_at"]}',f'Input SHA-256: {result["input_sha256"]}','',
      '## Supported consequences',f'{summary["communities_with_longer_routes"]} community reference points have longer routes; {summary["communities_newly_disconnected"]} lose access within the study graph.',
      'Affected population: unavailable.','', '| Community | Baseline km | Scenario km | Alternative facility |','| --- | --- | --- | --- |']
    km=lambda n:'No route' if n is None else f'{n/1000:.3f}'
    safe=lambda value:str(value or 'None').replace('|','/').replace('\n',' ')
    for row in result['communities']: lines.append(f'| {safe(row["name"])} | {km(row["baseline_m"])} | {km(row["scenario_m"])} | {safe(row["alternative_facility"])} |')
    lines+=['','## Alternatives for review']
    for option in result['alternatives']: lines += [f'- {option["action"]}: {option["reconnected_communities"]} reference points reconnected; {option.get("communities_with_shorter_routes","not recorded")} shorter routes; {option.get("mean_distance_saved_m",0):.1f} metres mean reduction among improved connected routes; {option["distance_saved_m"]:.1f} summed reference-point metres saved. {option["assumption"]}']
    lines+=['','## Limits and verification tasks']+['- '+v for v in result['limitations']]
    if result.get('live_alert_context'):
        context=result['live_alert_context']
        lines+=['','## Attached official alert context',str(context['alert'].get('headline') or context['alert'].get('event')),
          f'Source: {context["source_url"]}',f'Retrieved: {context["retrieved_at"]}',context['effect']]
    lines+=['','## Documented service scope']
    for facility in result.get('facility_scope',[]):
        lines.append(f'- {facility["name"]}: {facility.get("service_source","Source unavailable")} (reviewed {facility.get("service_reviewed_on","unknown")}; live availability unverified).')
    return '\n'.join(lines)+'\n'

def router(db):
    api=APIRouter(prefix='/continuity',tags=['Hospital continuity'])
    def view(row): return {'id':row.id,'region':row.region,'created_at':row.created_at,'request':row.request,'result':row.result}
    @api.get('/regions')
    def regions():
        result=[]
        for identifier,region in PILOTS.items():
            try:
                _,communities,facilities,manifest=dataset(identifier)
                result.append({'id':identifier,**region,'ready':True,'communities':communities,'facilities':facilities,'snapshot_at':manifest['download_completed_utc']})
            except (OSError,ValueError): result.append({'id':identifier,**region,'ready':False,'communities':[],'facilities':[],'snapshot_at':None})
        return result
    @api.post('/cases',status_code=201)
    def create(body:CaseRequest):
        try: result=calculate_case(body)
        except ValueError as exc: raise HTTPException(422,str(exc)) from exc
        except OSError as exc: raise HTTPException(503,'This region has no verified dataset') from exc
        if body.context_alert:
            feed=signals(body.region)
            if feed['alerts']['status']!='available': raise HTTPException(503,'Cannot verify selected alert context')
            alert=next((a for a in feed['alerts']['data'] if a['id']==body.context_alert),None)
            if alert is None: raise HTTPException(422,'Selected alert is no longer present in the regional feed')
            result['live_alert_context']={'alert':alert,'retrieved_at':feed['alerts']['retrieved_at'],'source_url':feed['alerts']['source_url'],'effect':'Context only; does not establish a facility outage or road closure.'}
        with db.sessions.begin() as session:
            row=ContinuityCaseRow(region=body.region,request=body.model_dump(mode='json'),result=result)
            session.add(row);session.flush();return view(row)
    @api.get('/cases')
    def cases(region:Literal['houston','alabama']):
        with db.sessions() as session:
            rows=session.scalars(select(ContinuityCaseRow).where(ContinuityCaseRow.region==region).order_by(ContinuityCaseRow.created_at.desc()).limit(30))
            return [view(row) for row in rows]
    @api.get('/signals/{region}')
    def regional_signals(region:Literal['houston','alabama']): return signals(region)
    @api.get('/cases/{case_id}')
    def case(case_id:str):
        with db.sessions() as session:
            row=session.get(ContinuityCaseRow,case_id)
            if not row: raise HTTPException(404,'Continuity case not found')
            return view(row)
    @api.get('/cases/{case_id}/brief',response_class=PlainTextResponse)
    def brief(case_id:str):
        return PlainTextResponse(render_brief(case(case_id)),media_type='text/markdown',headers={'Content-Disposition':f'attachment; filename="continuity-{case_id}.md"'})
    return api
