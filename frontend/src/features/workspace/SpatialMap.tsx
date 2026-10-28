import { useEffect, useRef, useState } from 'react'
import { Map as GLMap, Marker, Popup, NavigationControl, ScaleControl, setWorkerUrl, setWorkerCount, type GeoJSONSource, type StyleSpecification } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Crosshair, RotateCw, Box, Map as MapIcon } from 'lucide-react'
import type { AtlasData, RouteRow, Scenario } from '../../api'
import { collection, line, places, routeGeometry, closureGeometry } from './spatial'

export interface MapProps {
  atlas: AtlasData; selected: string; baseline?: RouteRow; active?: RouteRow; scenario?: Scenario;
  reopened: string[]; showFacilities: boolean; showOrigins: boolean; showRoads: boolean;
  onOrigin: (id: string) => void; onFacility: (id: string) => void
  onRoad?: (road:{u:number;v:number;name?:string}) => void
  selectedRoads?: {id:string;u:number;v:number}[]
}
const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
setWorkerUrl(workerUrl)
setWorkerCount(1)
const style: StyleSpecification = { version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#101a27' } }] }

export default function SpatialMap(props: MapProps) {
  const host = useRef<HTMLDivElement>(null), map = useRef<GLMap | null>(null)
  const callbacks = useRef(props); callbacks.current = props
  const labels = useRef<{ id: string; element: HTMLButtonElement; marker: Marker }[]>([])
  const [ready, setReady] = useState(false), [fallback, setFallback] = useState(false), [pitched, setPitched] = useState(false)
  const [streets,setStreets] = useState(true), [tileError,setTileError] = useState(false)
  const reset = () => { const [w,s,e,n] = props.atlas.manifest.bbox_wsen; map.current?.resize(); map.current?.fitBounds([[w,s],[e,n]], { padding: { top: 65, bottom: 60, left: 35, right: 35 }, duration: reduceMotion() ? 0 : 700, bearing: 0, pitch: 0 }); setPitched(false) }
  useEffect(() => {
    let disposed = false
    const startupTimeout = window.setTimeout(() => { if (!disposed) setFallback(true) }, 12000)
    setFallback(false)
    setReady(false)
    let instance: GLMap
    try {
      instance = new GLMap({ container: host.current!, style, center: [(props.atlas.manifest.bbox_wsen[0]+props.atlas.manifest.bbox_wsen[2])/2,(props.atlas.manifest.bbox_wsen[1]+props.atlas.manifest.bbox_wsen[3])/2], zoom: 13.6, minZoom: 11.5, maxZoom: 18, attributionControl: false,  canvasContextAttributes: { antialias: true } })
      map.current = instance
      instance.addControl(new NavigationControl({ visualizePitch: true }), 'bottom-right')
      instance.addControl(new ScaleControl({ unit: 'metric', maxWidth: 100 }), 'bottom-left')
      instance.on('load', () => {
        if (disposed) return
        window.clearTimeout(startupTimeout)
        const atlas = callbacks.current.atlas
        instance.addSource('street-tiles', {type:'raster',tiles:[import.meta.env.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,maxzoom:19,attribution:'© OpenStreetMap contributors'})
        instance.addLayer({id:'street-basemap',type:'raster',source:'street-tiles',paint:{'raster-opacity':.9}})
        const [w,s,e,n] = atlas.manifest.bbox_wsen
        const grid = []
        for (let x = w; x <= e; x += .005) grid.push(line([[x,s],[x,n]]))
        for (let y = s; y <= n; y += .005) grid.push(line([[w,y],[e,y]]))
        instance.addSource('grid', { type: 'geojson', data: collection(grid) })
        instance.addLayer({ id: 'coordinate-grid', type: 'line', source: 'grid', paint: { 'line-color': '#4b687f', 'line-width': .7, 'line-opacity': .18, 'line-dasharray': [1,5] } })
        instance.addSource('roads', { type: 'geojson', data: collection(atlas.road_features ? atlas.road_features.map(r => line(r.coordinates,{kind:r.kind,u:r.u,v:r.v,name:r.name || 'Unnamed road'})) : atlas.roads.map(r => line(r))) })
        instance.addLayer({ id: 'road-glow', type: 'line', source: 'roads', paint: { 'line-color': '#4c8796', 'line-width': 5, 'line-opacity': .07, 'line-blur': 3 } })
        instance.addLayer({ id: 'road-lines', type: 'line', source: 'roads', paint: { 'line-color': ['match',['get','kind'],['primary','secondary','tertiary'],'#74889d','#475e75'], 'line-width': ['interpolate',['linear'],['zoom'],12,.7,16,2.4], 'line-opacity': .85 } })
        const roadPopup=new Popup({closeButton:false,closeOnClick:false,offset:12})
        instance.addLayer({id:'road-hit',type:'line',source:'roads',paint:{'line-width':16,'line-opacity':0}})
        instance.on('click','road-hit',event=>{const road=event.features?.[0]?.properties;if(road&&Number.isFinite(Number(road.u))&&Number.isFinite(Number(road.v))) callbacks.current.onRoad?.({u:Number(road.u),v:Number(road.v),name:String(road.name)})})
        instance.on('mousemove','road-hit',event=>{const road=event.features?.[0]?.properties;if(road) roadPopup.setLngLat(event.lngLat).setText(`${road.name} · click to toggle closure selection`).addTo(instance)})
        instance.on('mouseleave','road-hit',()=>roadPopup.remove())
        for (const id of ['baseline','active','closures','draft-closures']) instance.addSource(id, { type: 'geojson', data: collection([]) })
        instance.addLayer({id:'draft-closures',type:'line',source:'draft-closures',paint:{'line-color':'#f6b73c','line-width':7,'line-dasharray':[2,1]}})
        instance.addLayer({ id: 'baseline-glow', type: 'line', source: 'baseline', paint: { 'line-color': '#4dd6c3', 'line-width': 13, 'line-blur': 8, 'line-opacity': .3 } })
        instance.addLayer({ id: 'baseline-line', type: 'line', source: 'baseline', paint: { 'line-color': '#4dd6c3', 'line-width': 3.5, 'line-opacity': .9 } })
        instance.addLayer({ id: 'active-line', type: 'line', source: 'active', paint: { 'line-color': '#bda1ff', 'line-width': 4, 'line-dasharray': [2,1] } })
        instance.addLayer({ id: 'closure-glow', type: 'line', source: 'closures', paint: { 'line-color': '#ff806c', 'line-width': 13, 'line-opacity': .2 } })
        instance.addLayer({ id: 'closure-line', type: 'line', source: 'closures', paint: { 'line-color': '#ff806c', 'line-width': 5 } })
        for (const type of ['origins','facilities'] as const) instance.addSource(type, { type: 'geojson', data: places(atlas,type) })
        instance.addLayer({ id: 'facilities', type: 'circle', source: 'facilities', paint: { 'circle-radius': 4, 'circle-color': '#c5d9e7', 'circle-stroke-color': '#1c3143', 'circle-stroke-width': 2 } })
        instance.addLayer({ id: 'origin-halo', type: 'circle', source: 'origins', paint: { 'circle-radius': 15, 'circle-color': '#4dd6c3', 'circle-opacity': .1 } })
        instance.addLayer({ id: 'origins', type: 'circle', source: 'origins', paint: { 'circle-radius': 5, 'circle-color': '#4dd6c3', 'circle-stroke-color': '#10272b', 'circle-stroke-width': 2 } })
        instance.addSource('selected', { type: 'geojson', data: collection([]) })
        instance.addLayer({ id: 'selected-ring', type: 'circle', source: 'selected', paint: { 'circle-radius': 11, 'circle-color': '#4dd6c3', 'circle-opacity': .12, 'circle-stroke-color': '#85f1dc', 'circle-stroke-width': 1 } })
        labels.current = atlas.origins.map(origin => {
          const element = document.createElement('button')
          element.type = 'button'; element.className = 'map-origin-label'; element.textContent = origin.id
          element.setAttribute('aria-label', `Map origin ${origin.id}`)
          element.addEventListener('click', event => { event.stopPropagation(); callbacks.current.onOrigin(origin.id) })
          const marker = new Marker({ element, anchor: 'bottom', offset: [0,-13] }).setLngLat([origin.lon,origin.lat]).addTo(instance)
          return { id: origin.id, element, marker }
        })
        const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 12 })
        instance.on('mousemove','facilities',event => {
          const label = event.features?.[0]?.properties?.label
          if (typeof label === 'string') popup.setLngLat(event.lngLat).setText(`${label} · cached hospital record`).addTo(instance)
        })
        instance.on('mouseleave','facilities',()=>popup.remove())
        for (const id of ['origins','facilities']) {
          instance.on('mouseenter', id, () => { instance.getCanvas().style.cursor = 'pointer' })
          instance.on('mouseleave', id, () => { instance.getCanvas().style.cursor = '' })
          instance.on('click', id, event => { const key = event.features?.[0]?.properties?.id; if (typeof key === 'string') { if (id === 'origins') callbacks.current.onOrigin(key); else callbacks.current.onFacility(key) } })
        }
        reset(); setReady(true)
      })
      instance.on('error', event => { if (!disposed) { if ('sourceId' in event && event.sourceId === 'street-tiles') setTileError(true); else setFallback(true) } })
      const contextLost = () => { if (!disposed) setFallback(true) }
      instance.getCanvas().addEventListener('webglcontextlost', contextLost)
      const observer = new ResizeObserver(() => instance.resize()); observer.observe(host.current!)
        return () => { disposed = true; window.clearTimeout(startupTimeout); observer.disconnect(); labels.current.forEach(l=>l.marker.remove()); labels.current=[]; instance.getCanvas().removeEventListener('webglcontextlost', contextLost); instance.remove(); map.current = null }
    } catch (error) { window.clearTimeout(startupTimeout); console.warn('Local map initialization failed', error); setFallback(true) }
  }, [props.atlas])
  useEffect(() => {
    const instance = map.current; if (!ready || !instance || fallback) return
    instance.setLayoutProperty('street-basemap','visibility',streets?'visible':'none')
    const set = (id: string, data: ReturnType<typeof collection>) => (instance.getSource(id) as GeoJSONSource)?.setData(data)
    set('baseline', routeGeometry(props.atlas, props.baseline)); set('active', routeGeometry(props.atlas, props.active)); set('closures', closureGeometry(props.atlas, props.scenario, props.reopened))
    set('draft-closures',collection((props.selectedRoads ?? []).flatMap(c=>props.atlas.road_features?.filter(r=>(r.u===c.u&&r.v===c.v)||(r.u===c.v&&r.v===c.u)).map(r=>line(r.coordinates)) ?? [])))
    const p = props.atlas.origins.find(p => p.id === props.selected)
    set('selected', collection(p ? [{ type: 'Feature', geometry: { type: 'Point', coordinates: [p.lon,p.lat] }, properties: {} }] : []))
    labels.current.forEach(label => { label.element.style.display = props.showOrigins ? '' : 'none'; label.element.classList.toggle('active',label.id===props.selected) })
    for (const [ids, show] of [[['facilities'],props.showFacilities],[['origins','origin-halo','selected-ring'],props.showOrigins],[['road-lines','road-glow'],props.showRoads]] as const)
      for (const id of ids) instance.setLayoutProperty(id,'visibility',show ? 'visible' : 'none')
  }, [ready, props, streets, fallback])
  return <div className="spatial-map" data-renderer={fallback ? "compatibility" : ready ? "maplibre" : "initializing"}><div className="gl-host" style={{visibility:fallback?'hidden':'visible'}} ref={host} aria-label="Interactive study-area network map"/>{fallback && <FallbackMap {...props} streets={streets}/>}
    <div className="map-hud"><span className="hud-cross">+</span><span>{((props.atlas.manifest.bbox_wsen[1]+props.atlas.manifest.bbox_wsen[3])/2).toFixed(4)}° N<br/>{Math.abs((props.atlas.manifest.bbox_wsen[0]+props.atlas.manifest.bbox_wsen[2])/2).toFixed(4)}° {props.atlas.manifest.bbox_wsen[0] < 0 ? "W" : "E"}</span><span className="hud-line"/><span>{props.atlas.manifest.area?.includes("Houston") ? "HOUSTON · TEXAS" : "HEIDELBERG"}<br/><b>LOCAL STUDY NETWORK</b></span></div>
    <div className="map-actions"><button aria-label="Toggle street basemap" aria-pressed={streets} onClick={()=>setStreets(value=>!value)}><MapIcon size={17}/></button><button onClick={reset} disabled={fallback} aria-label="Fit study network"><Crosshair size={17}/></button><button aria-label="Toggle perspective" aria-pressed={pitched} disabled={fallback} onClick={() => { map.current?.easeTo({ pitch: pitched ? 0 : 45, bearing: pitched ? 0 : -18, duration: reduceMotion() ? 0 : 700 }); setPitched(!pitched) }}>{pitched ? <MapIcon size={17}/> : <Box size={17}/>}</button><button aria-label="Reset bearing" disabled={fallback} onClick={() => map.current?.easeTo({ bearing: 0, duration: reduceMotion() ? 0 : 400 })}><RotateCw size={16}/></button></div>
    <div className="map-source"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors · ODbL</a><span>{fallback ? 'Compatibility view · WebGL unavailable' : tileError ? 'Street tiles unavailable · cached roads remain usable' : streets ? 'OSM street map · click roads to select' : 'Offline network view'}</span></div>
  </div>
}

function FallbackMap(props: MapProps & {streets:boolean}) {
  const [zoom,setZoom]=useState(1)
  const [w,s,e,n] = props.atlas.manifest.bbox_wsen
  const cos=Math.cos((s+n)/2*Math.PI/180),scale=Math.min(660/((e-w)*cos),500/(n-s))
  const p = ([x,y]: number[]) => [400+(x-(w+e)/2)*cos*scale,300-(y-(n+s)/2)*scale]
  const d = (coords: number[][]) => coords.map((c,i) => `${i?'L':'M'}${p(c).join(',')}`).join(' ')
  const lines=(source:ReturnType<typeof routeGeometry>)=>source.features.flatMap(f=>f.geometry.type==='LineString'?[f.geometry.coordinates]:[])
  const z=13,N=2**z
  const tx=(lon:number)=>Math.floor((lon+180)/360*N)
  const ty=(lat:number)=>Math.floor((1-Math.asinh(Math.tan(lat*Math.PI/180))/Math.PI)/2*N)
  const lat=(y:number)=>Math.atan(Math.sinh(Math.PI*(1-2*y/N)))*180/Math.PI
  const tiles=[]
  for(let x=tx(w);x<=tx(e);x++)for(let y=ty(n);y<=ty(s);y++){
    const a=p([x/N*360-180,lat(y)]),b=p([(x+1)/N*360-180,lat(y+1)])
    const url=(import.meta.env.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png').replace('{z}',String(z)).replace('{x}',String(x)).replace('{y}',String(y))
    tiles.push(<image key={`${x}/${y}`} href={url} x={a[0]} y={a[1]} width={b[0]-a[0]} height={b[1]-a[1]} preserveAspectRatio="none"/> )
  }
  const selected=(u:number,v:number)=>props.selectedRoads?.some(r=>(r.u===u&&r.v===v)||(r.u===v&&r.v===u))
  const names=new Set<string>()
  return <><svg className="fallback-map" viewBox="0 0 800 600" role="img" aria-label="Compatibility rendering of actual cached study-area geometry"><g transform={`translate(400 300) scale(${zoom}) translate(-400 -300)`}>
    {props.streets&&<g opacity=".9">{tiles}</g>}
    <g fill="none" stroke="#536b80" strokeWidth="1">{props.showRoads && props.atlas.roads.map((r,i)=><path key={i} d={d(r)}/>)}</g>
    {props.showRoads&&props.atlas.road_features?.map((r,i)=><path key={'hit'+i} d={d(r.coordinates)} fill="none" stroke={selected(r.u,r.v)?'#f6b73c':'transparent'} strokeWidth={selected(r.u,r.v)?5:12} style={{cursor:'pointer'}} onClick={()=>props.onRoad?.(r)}><title>{r.name || 'Unnamed road'} · click to toggle closure selection</title></path>)}
    {!props.streets&&props.atlas.road_features?.flatMap((r,i)=>{if(!r.name||names.has(r.name))return [];names.add(r.name);const point=p(r.coordinates[Math.floor(r.coordinates.length/2)]);return [<text key={'name'+i} x={point[0]} y={point[1]} fill="#dbe6ed" stroke="#101a27" strokeWidth="2" paintOrder="stroke" fontSize="8">{r.name}</text>]})}
    {lines(routeGeometry(props.atlas,props.baseline)).map((r,i)=><path key={'base'+i} d={d(r)} fill="none" stroke="#008c7d" strokeWidth="4" pointerEvents="none"/>)}
    {lines(routeGeometry(props.atlas,props.active)).map((r,i)=><path key={'active'+i} d={d(r)} fill="none" stroke="#7546c9" strokeWidth="4" pointerEvents="none"/>)}
    {lines(closureGeometry(props.atlas,props.scenario,props.reopened)).map((r,i)=><path key={'closure'+i} d={d(r)} fill="none" stroke="#e54631" strokeWidth="5" pointerEvents="none"/>)}
    {props.showFacilities&&props.atlas.facilities.map(f=><g key={f.id} onClick={()=>props.onFacility(f.id)} style={{cursor:'pointer'}}><title>{f.name || f.id}</title><rect x={p([f.lon,f.lat])[0]-4} y={p([f.lon,f.lat])[1]-4} width="8" height="8" fill="#bb2945" stroke="white"/></g>)}
    {props.showOrigins && props.atlas.origins.map(o=><g key={o.id} onClick={()=>props.onOrigin(o.id)} style={{cursor:'pointer'}}><circle cx={p([o.lon,o.lat])[0]} cy={p([o.lon,o.lat])[1]} r="6" fill="#007e72" stroke="white"/><text x={p([o.lon,o.lat])[0]+8} y={p([o.lon,o.lat])[1]-8} fill="#007e72" stroke="white" strokeWidth="2" paintOrder="stroke" fontSize="11">{o.id}</text></g>)}
  </g></svg><div className="fallback-controls"><button onClick={()=>setZoom(z=>Math.min(2,z+.2))} disabled={zoom>=2}>Zoom in</button><button onClick={()=>setZoom(z=>Math.max(.6,z-.2))} disabled={zoom<=.6}>Zoom out</button><button onClick={()=>setZoom(1)}>Fit compatibility view</button></div></>
}
