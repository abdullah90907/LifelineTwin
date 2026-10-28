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
  const reset = () => { const [w,s,e,n] = props.atlas.manifest.bbox_wsen; map.current?.resize(); map.current?.fitBounds([[w,s],[e,n]], { padding: { top: 65, bottom: 60, left: 35, right: 35 }, duration: reduceMotion() ? 0 : 700, bearing: 0, pitch: 0 }); setPitched(false) }
  useEffect(() => {
    let disposed = false
    const startupTimeout = window.setTimeout(() => { if (!disposed) setFallback(true) }, 12000)
    setFallback(false)
    setReady(false)
    let instance: GLMap
    try {
      instance = new GLMap({ container: host.current!, style, center: [8.6775,49.415], zoom: 13.6, minZoom: 11.5, maxZoom: 18, attributionControl: false, maxBounds: [[8.60,49.36],[8.76,49.48]], canvasContextAttributes: { antialias: true } })
      map.current = instance
      instance.addControl(new NavigationControl({ visualizePitch: true }), 'bottom-right')
      instance.addControl(new ScaleControl({ unit: 'metric', maxWidth: 100 }), 'bottom-left')
      instance.on('load', () => {
        if (disposed) return
        window.clearTimeout(startupTimeout)
        const atlas = callbacks.current.atlas
        const [w,s,e,n] = atlas.manifest.bbox_wsen
        const grid = []
        for (let x = w; x <= e; x += .005) grid.push(line([[x,s],[x,n]]))
        for (let y = s; y <= n; y += .005) grid.push(line([[w,y],[e,y]]))
        instance.addSource('grid', { type: 'geojson', data: collection(grid) })
        instance.addLayer({ id: 'coordinate-grid', type: 'line', source: 'grid', paint: { 'line-color': '#4b687f', 'line-width': .7, 'line-opacity': .18, 'line-dasharray': [1,5] } })
        instance.addSource('roads', { type: 'geojson', data: collection(atlas.road_features ? atlas.road_features.map(r => line(r.coordinates,{kind:r.kind})) : atlas.roads.map(r => line(r))) })
        instance.addLayer({ id: 'road-glow', type: 'line', source: 'roads', paint: { 'line-color': '#4c8796', 'line-width': 5, 'line-opacity': .07, 'line-blur': 3 } })
        instance.addLayer({ id: 'road-lines', type: 'line', source: 'roads', paint: { 'line-color': ['match',['get','kind'],['primary','secondary','tertiary'],'#74889d','#475e75'], 'line-width': ['interpolate',['linear'],['zoom'],12,.7,16,2.4], 'line-opacity': .85 } })
        for (const id of ['baseline','active','closures']) instance.addSource(id, { type: 'geojson', data: collection([]) })
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
      instance.on('error', () => { if (!disposed) setFallback(true) })
      const contextLost = () => { if (!disposed) setFallback(true) }
      instance.getCanvas().addEventListener('webglcontextlost', contextLost)
      const observer = new ResizeObserver(() => instance.resize()); observer.observe(host.current!)
        return () => { disposed = true; window.clearTimeout(startupTimeout); observer.disconnect(); labels.current.forEach(l=>l.marker.remove()); labels.current=[]; instance.getCanvas().removeEventListener('webglcontextlost', contextLost); instance.remove(); map.current = null }
    } catch (error) { window.clearTimeout(startupTimeout); console.warn('Local map initialization failed', error); setFallback(true) }
  }, [props.atlas])
  useEffect(() => {
    const instance = map.current; if (!ready || !instance) return
    const set = (id: string, data: ReturnType<typeof collection>) => (instance.getSource(id) as GeoJSONSource)?.setData(data)
    set('baseline', routeGeometry(props.atlas, props.baseline)); set('active', routeGeometry(props.atlas, props.active)); set('closures', closureGeometry(props.atlas, props.scenario, props.reopened))
    const p = props.atlas.origins.find(p => p.id === props.selected)
    set('selected', collection(p ? [{ type: 'Feature', geometry: { type: 'Point', coordinates: [p.lon,p.lat] }, properties: {} }] : []))
    labels.current.forEach(label => { label.element.style.display = props.showOrigins ? '' : 'none'; label.element.classList.toggle('active',label.id===props.selected) })
    for (const [ids, show] of [[['facilities'],props.showFacilities],[['origins','origin-halo','selected-ring'],props.showOrigins],[['road-lines','road-glow'],props.showRoads]] as const)
      for (const id of ids) instance.setLayoutProperty(id,'visibility',show ? 'visible' : 'none')
  }, [ready, props])
  return <div className="spatial-map" data-renderer={fallback ? "compatibility" : ready ? "maplibre" : "initializing"}><div className="gl-host" ref={host} aria-label="Interactive Heidelberg network map"/>{fallback && <FallbackMap {...props}/>}
    <div className="map-hud"><span className="hud-cross">+</span><span>49.4150° N<br/>8.6775° E</span><span className="hud-line"/><span>HEIDELBERG<br/><b>LOCAL STUDY NETWORK</b></span></div>
    <div className="map-actions"><button onClick={reset} disabled={fallback} aria-label="Fit study network"><Crosshair size={17}/></button><button aria-label="Toggle perspective" aria-pressed={pitched} disabled={fallback} onClick={() => { map.current?.easeTo({ pitch: pitched ? 0 : 45, bearing: pitched ? 0 : -18, duration: reduceMotion() ? 0 : 700 }); setPitched(!pitched) }}>{pitched ? <MapIcon size={17}/> : <Box size={17}/>}</button><button aria-label="Reset bearing" disabled={fallback} onClick={() => map.current?.easeTo({ bearing: 0, duration: reduceMotion() ? 0 : 400 })}><RotateCw size={16}/></button></div>
    <div className="map-source"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors · ODbL</a><span>{fallback ? 'Compatibility view · WebGL unavailable' : 'Local geometry · no external tiles'}</span></div>
  </div>
}

function FallbackMap(props: MapProps) {
  const [zoom,setZoom]=useState(1)
  const [w,s,e,n] = props.atlas.manifest.bbox_wsen
  const cos=Math.cos((s+n)/2*Math.PI/180),scale=Math.min(660/((e-w)*cos),500/(n-s))
  const p = ([x,y]: number[]) => [400+(x-(w+e)/2)*cos*scale,300-(y-(n+s)/2)*scale]
  const d = (coords: number[][]) => coords.map((c,i) => `${i?'L':'M'}${p(c).join(',')}`).join(' ')
  const lines=(source:ReturnType<typeof routeGeometry>)=>source.features.flatMap(f=>f.geometry.type==='LineString'?[f.geometry.coordinates]:[])
  return <><svg className="fallback-map" viewBox="0 0 800 600" role="img" aria-label="Compatibility rendering of actual cached Heidelberg geometry"><g transform={`translate(400 300) scale(${zoom}) translate(-400 -300)`}><g fill="none" stroke="#536b80" strokeWidth="1">{props.showRoads && props.atlas.roads.map((r,i)=><path key={i} d={d(r)}/>)}</g>{lines(routeGeometry(props.atlas,props.baseline)).map((r,i)=><path key={'base'+i} d={d(r)} fill="none" stroke="#4dd6c3" strokeWidth="3"/>)}{lines(routeGeometry(props.atlas,props.active)).map((r,i)=><path key={'active'+i} d={d(r)} fill="none" stroke="#bda1ff" strokeWidth="3"/>)}{lines(closureGeometry(props.atlas,props.scenario,props.reopened)).map((r,i)=><path key={'closure'+i} d={d(r)} fill="none" stroke="#ff806c" strokeWidth="4"/>)}{props.showFacilities&&props.atlas.facilities.map(f=><rect key={f.id} x={p([f.lon,f.lat])[0]-3} y={p([f.lon,f.lat])[1]-3} width="6" height="6" fill="#c5d9e7"/>)}{props.showOrigins && props.atlas.origins.map(o=><g key={o.id}><circle cx={p([o.lon,o.lat])[0]} cy={p([o.lon,o.lat])[1]} r="5" fill="#4dd6c3"/><text x={p([o.lon,o.lat])[0]+8} y={p([o.lon,o.lat])[1]-8} fill="#c3e9df" fontSize="9">{o.id}</text></g>)}</g></svg><div className="fallback-controls"><button onClick={()=>setZoom(z=>Math.min(2,z+.2))} disabled={zoom>=2}>Zoom in</button><button onClick={()=>setZoom(z=>Math.max(.6,z-.2))} disabled={zoom<=.6}>Zoom out</button><button onClick={()=>setZoom(1)}>Fit compatibility view</button></div></>
}

