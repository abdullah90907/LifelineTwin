"""Explicitly acquire real Houston geography and weather; retain existing caches."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lifelinetwin_geo.data import download
from lifelinetwin_geo.weather import fetch_forecast

def hospital_geometry(target):
    """Direct OSM map endpoint fallback; retains actual tagged node/way geometry."""
    import requests
    import xml.etree.ElementTree as ET
    import geopandas as gpd
    from shapely.geometry import Point, Polygon
    source=target/'medical-center.osm'
    if not source.exists():
        response=requests.get('https://api.openstreetmap.org/api/0.6/map',params={
            'bbox':'-95.408,29.697,-95.383,29.724'},headers={
            'User-Agent':'LifelineTwin/1.0 (https://github.com/abdullah90907/LifelineTwin)'},timeout=(5,40))
        response.raise_for_status()
        source.write_bytes(response.content)
    root=ET.parse(source).getroot()
    nodes={n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in root.findall('node')}
    rows=[]
    for item in root:
        tags={tag.attrib['k']:tag.attrib['v'] for tag in item.findall('tag')}
        if tags.get('amenity')!='hospital':
            continue
        if item.tag=='node':
            geometry=Point(nodes[item.attrib['id']])
        elif item.tag=='way':
            coordinates=[nodes[n.attrib['ref']] for n in item.findall('nd')]
            if len(coordinates)<4 or coordinates[0]!=coordinates[-1]:
                continue
            geometry=Polygon(coordinates)
        else:
            continue  # relations are not reconstructed or counted as complete facilities
        rows.append({'element':item.tag,'id':int(item.attrib['id']),'name':tags.get('name'),
                     'geometry':geometry,'source':'OpenStreetMap API 0.6 map'})
    gpd.GeoDataFrame(rows,crs='EPSG:4326').to_file(target/'hospitals.geojson',driver='GeoJSON')

if __name__ == '__main__':
    import osmnx as ox
    ox.settings.log_console=True
    ox.settings.overpass_url='https://overpass.private.coffee/api'
    ox.settings.overpass_rate_limit=False
    target=ROOT/'data/houston'
    target.mkdir(parents=True,exist_ok=True)
    if not (target/'hospitals.geojson').exists():
        hospital_geometry(target)
    print(download(target,bbox=(-95.43,29.68,-95.36,29.735),area='Texas Medical Center and Brays Bayou, Houston, Texas, USA',grid=(.1,.3,.5,.7,.9)),flush=True)
    manifest_file=target/'manifest.json'
    manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
    manifest['hospital_source']='OpenStreetMap API 0.6 map; tagged hospital nodes and closed ways only; relations excluded'
    manifest['hospital_bbox_wsen']=[-95.408,29.697,-95.383,29.724]
    manifest_file.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    weather=target/'weather/obs_current-context.json'
    if not weather.exists():
        result=fetch_forecast(lat=29.7075,lon=-95.395,past_days=30,forecast_days=2)
        weather.parent.mkdir(parents=True,exist_ok=True)
        weather.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    print('Houston geography and weather prepared.',flush=True)
