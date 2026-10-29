"""Extract named OSM reference places; never relabel grid points as communities."""
import sys,json
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lifelinetwin_geo.data import load,snap,write_json,digest

if __name__=='__main__':
    folder=ROOT/'data/houston'
    graph,_,_,manifest=load(folder)
    west,south,east,north=manifest['bbox_wsen']
    places=[]
    for node in ET.parse(folder/'medical-center.osm').getroot().findall('node'):
        tags={tag.attrib['k']:tag.attrib['v'] for tag in node.findall('tag')}
        lon,lat=float(node.attrib['lon']),float(node.attrib['lat'])
        if tags.get('place') not in ('city','town','village','suburb','neighbourhood') or not tags.get('name') or not(west<=lon<=east and south<=lat<=north): continue
        snapped,offset=snap(graph,lon,lat)
        places.append({'id':'place/'+node.attrib['id'],'name':tags['name'],'lat':lat,'lon':lon,'node':snapped,'snap_distance_m':offset,'source':'https://www.openstreetmap.org/node/'+node.attrib['id'],'population':None})
    if not places: raise ValueError('No named places found')
    write_json(folder/'communities.json',places)
    manifest['sha256']['communities.json']=digest(folder/'communities.json')
    write_json(folder/'manifest.json',manifest)
    print(f'{len(places)} named Houston reference points prepared')
