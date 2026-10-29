"""Acquire a bounded Tuscaloosa–Northport–Moundville pilot, without overwriting caches."""
import sys, json, time
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import requests
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point, Polygon
from lifelinetwin_geo.data import snap, write_json, digest, load
from datetime import datetime, timezone

BBOX=(-87.71,32.97,-87.46,33.29)
DRIVABLE={'motorway','motorway_link','trunk','trunk_link','primary','primary_link','secondary','secondary_link','tertiary','tertiary_link','unclassified','residential','living_street','service'}

def prepare():
    target=ROOT/'data/alabama'; target.mkdir(parents=True,exist_ok=True)
    if (target/'manifest.json').exists():
        load(target); print('Existing Alabama cache verified.'); return
    elements={}
    def cell(bbox,key,depth=0):
        raw=target/f'raw-{key}.osm'
        if not raw.exists():
            print(f'Acquiring Alabama cell {key}',flush=True)
            response=requests.get('https://api.openstreetmap.org/api/0.6/map',params={'bbox':','.join(f'{v:.7f}' for v in bbox)},headers={'User-Agent':'LifelineTwin/1.0 (https://github.com/abdullah90907/LifelineTwin)'},timeout=(10,90))
            if response.status_code==400 and 'too many nodes' in response.text.lower() and depth<7:
                w,s,e,n=bbox
                if e-w>n-s:
                    cell((w,s,(w+e)/2,n),key+'a',depth+1); cell(((w+e)/2,s,e,n),key+'b',depth+1)
                else:
                    cell((w,s,e,(s+n)/2),key+'a',depth+1); cell((w,(s+n)/2,e,n),key+'b',depth+1)
                return
            response.raise_for_status(); raw.write_bytes(response.content)
        for item in ET.parse(raw).getroot():
            if item.tag in ('node','way'): elements[(item.tag,item.attrib['id'])]=item
    west,south,east,north=BBOX
    for ix in range(2):
        for iy in range(3):
            bbox=(west+(east-west)*ix/2,south+(north-south)*iy/3,west+(east-west)*(ix+1)/2,south+(north-south)*(iy+1)/3)
            cell(bbox,f'{ix}-{iy}')
    nodes={key[1]:(float(item.attrib['lon']),float(item.attrib['lat'])) for key,item in elements.items() if key[0]=='node'}
    tags=lambda item:{t.attrib['k']:t.attrib['v'] for t in item.findall('tag')}
    road_root=ET.Element('osm',version='0.6',generator='LifelineTwin')
    required=set(); ways=[]; hospitals=[]; communities=[]
    for (kind,identifier),item in elements.items():
        attrs=tags(item)
        if kind=='way' and attrs.get('highway') in DRIVABLE and attrs.get('access') not in ('no','private'):
            refs=[n.attrib['ref'] for n in item.findall('nd')]
            if all(ref in nodes for ref in refs): ways.append(item); required.update(refs)
        if attrs.get('amenity')=='hospital':
            if kind=='node': geometry=Point(nodes[identifier])
            else:
                refs=[n.attrib['ref'] for n in item.findall('nd')]
                if len(refs)<4 or refs[0]!=refs[-1] or not all(ref in nodes for ref in refs): continue
                geometry=Polygon([nodes[ref] for ref in refs])
            hospitals.append({'id':f'{kind}/{identifier}','name':attrs.get('name',f'OSM hospital {identifier}'),'geometry':geometry})
        if kind=='node' and attrs.get('place') in ('city','town','village','hamlet','suburb') and attrs.get('name'):
            lon,lat=nodes[identifier]
            if west<=lon<=east and south<=lat<=north:
                communities.append({'id':f'place/{identifier}','name':attrs['name'],'lon':lon,'lat':lat,'place_type':attrs['place'],'source':f'https://www.openstreetmap.org/node/{identifier}'})
    for identifier in required: road_root.append(elements[('node',identifier)])
    for way in ways: road_root.append(way)
    ET.ElementTree(road_root).write(target/'driving.osm',encoding='utf-8',xml_declaration=True)
    print('Building directed Alabama road graph',flush=True)
    graph=ox.graph_from_xml(target/'driving.osm',simplify=True,retain_all=True)
    ox.save_graphml(graph,target/'roads.graphml')
    facilities=[]
    for hospital in hospitals:
        point=hospital['geometry'].representative_point()
        node,offset=snap(graph,point.x,point.y)
        facilities.append({'id':hospital['id'],'name':hospital['name'],'lon':point.x,'lat':point.y,'node':node,'snap_distance_m':offset,'capability_status':'unverified','source':f'https://www.openstreetmap.org/{hospital["id"]}'})
    if len(facilities)<2: raise ValueError('Fewer than two hospital records; analysis remains disabled')
    origins=[]
    for community in sorted(communities,key=lambda c:c['name']):
        node,offset=snap(graph,community['lon'],community['lat'])
        if offset>1000: continue
        origins.append({**community,'node':node,'snap_distance_m':offset,'population':None})
    if len(origins)<3: raise ValueError('Too few verified named place points')
    gpd.GeoDataFrame(hospitals,crs='EPSG:4326').to_file(target/'hospitals.geojson',driver='GeoJSON')
    write_json(target/'facilities.json',facilities); write_json(target/'origins.json',origins)
    files=['roads.graphml','hospitals.geojson','facilities.json','origins.json']
    write_json(target/'manifest.json',{'area':'Tuscaloosa, Northport and Moundville, Alabama, USA','bbox_wsen':BBOX,'nodes':len(graph),'directed_edges':graph.number_of_edges(),'download_completed_utc':datetime.now(timezone.utc).isoformat(),'source':'OpenStreetMap API 0.6; filtered driving ways via OSMnx','origin_method':'Named OSM place reference points; not population centroids','attribution':'© OpenStreetMap contributors; ODbL https://www.openstreetmap.org/copyright','sha256':{name:digest(target/name) for name in files}})
    print(f'Alabama ready: {len(graph)} road nodes, {len(facilities)} facilities, {len(origins)} named places.',flush=True)

if __name__=='__main__': prepare()
