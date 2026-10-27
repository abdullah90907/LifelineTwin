import { useId, useState } from 'react'
import { ArrowUpRight, Layers, Minus, Plus, RotateCcw, AlertCircle, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { AtlasData, Baseline } from './api'

export function Brand() { return <Link className="brand" to="/" aria-label="LifelineTwin overview"><svg width="31" height="33" viewBox="0 0 32 34" aria-hidden="true"><path d="M4 6v18l12 7 12-7V6L16 0Z" fill="none" stroke="currentColor" strokeWidth="1.6"/><path d="m4 16 7 4 5-10 5 14 7-8M16 31V23" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/></svg><span>Lifeline<span className="brand-light">Twin</span><small>INTELLIGENCE IN CONTEXT</small></span></Link> }
export function Tag({ children, tone = '' }: { children: React.ReactNode; tone?: string }) { return <span className={`tag ${tone}`}>{children}</span> }
export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) { return <div className="error-state" role="alert"><AlertCircle size={18}/><span>{error instanceof Error ? error.message : 'Data could not be loaded.'}</span>{retry && <button className="text-button" onClick={retry}>Retry <RotateCcw size={13}/></button>}</div> }
export function SectionHeading({ index, title, children }: { index: string; title: string; children?: React.ReactNode }) { return <div className="section-heading"><h2><span>{index}</span>{title}</h2>{children}</div> }
export function NextLink({ to, children }: { to: string; children: React.ReactNode }) { return <Link className="text-link" to={to}>{children}<ArrowUpRight size={15}/></Link> }
export function date(value: string) { const parsed = new Date(value); return Number.isNaN(parsed.getTime()) ? 'Unknown date' : new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(parsed) }
export function distance(value: number | null | undefined) { return value == null ? 'No route' : value >= 1000 ? `${(value / 1000).toFixed(2)} km` : `${Math.round(value)} m` }

export function NetworkMap({ data, baseline, expanded = false }: { data: AtlasData; baseline?: Baseline; expanded?: boolean }) {
  const [selected, setSelected] = useState('O5')
  const [zoom, setZoom] = useState(1)
  const [facilities, setFacilities] = useState(true)
  const gridId = useId().replace(/:/g, '')
  const [west, south, east, north] = data.manifest.bbox_wsen
  const midLat = (south + north) / 2
  const cos = Math.cos(midLat * Math.PI / 180)
  const scale = Math.min(880 / ((east - west) * cos), 520 / (north - south))
  const project = ([lon, lat]: number[]) => [500 + (lon - (west + east) / 2) * cos * scale, 300 - (lat - midLat) * scale]
  const path = (line: number[][]) => line.map((c, i) => `${i ? 'L' : 'M'}${project(c).map(n => n.toFixed(2)).join(',')}`).join(' ')
  const route = baseline?.analysis.baseline.find(r => r.id === selected)
  const routeNodes = route?.path.map(n => data.nodes[String(n)]).filter(Boolean) ?? []
  return <div className={`network-map ${expanded ? 'expanded' : ''}`}>
    <div className="map-top"><span className="map-label"><span className="status-dot"/>HEIDELBERG <span className="map-label-muted">/ CACHED ROAD NETWORK</span></span><span className="north">N ↑</span></div>
    <svg className="map-canvas" viewBox="0 0 1000 600" role="img" aria-label="Cached Heidelberg road network with sampled grid origins, hospital records and selected baseline route">
      <defs><pattern id={gridId} width="55" height="55" patternUnits="userSpaceOnUse"><path d="M55 0H0V55" fill="none" stroke="#c3d6cf" strokeWidth=".6" opacity=".35"/></pattern></defs>
      <rect width="1000" height="600" fill={`url(#${gridId})`}/>
      <g transform={`translate(500 300) scale(${zoom}) translate(-500 -300)`}>
        <g fill="none" stroke="#78a896" strokeWidth="1.4" strokeLinecap="round" opacity=".7">{data.roads.map((road, i) => <path key={i} d={path(road)}/>)}</g>
        {routeNodes.length > 1 && <><path d={path(routeNodes)} fill="none" stroke="#fff" strokeWidth="8" opacity=".8"/><path className="route-path" d={path(routeNodes)} fill="none" stroke="#de6f50" strokeWidth="3.8" strokeLinecap="round"/></>}
        {facilities && data.facilities.map(p => { const [x, y] = project([p.lon, p.lat]); return <g key={p.id} transform={`translate(${x} ${y})`}><title>{p.name ?? p.id} · cached hospital record</title><rect x="-4" y="-4" width="8" height="8" rx="1.5" fill="#fff" stroke="#235f52" strokeWidth="1.2"/><path d="M-2 0H2M0-2V2" stroke="#235f52" strokeWidth="1"/></g> })}
        {data.origins.map(p => { const [x, y] = project([p.lon, p.lat]); return <g key={p.id} transform={`translate(${x} ${y})`} opacity={p.id === selected ? 1 : .8}><circle r={p.id === selected ? 15 : 9} fill={p.id === selected ? '#f3efd9' : '#2e5c4e'} stroke="#c4dbbf" strokeWidth="2"/><text y="3" textAnchor="middle" fill={p.id === selected ? '#264c40' : '#e3efdc'} fontSize="8" fontWeight="600">{p.id.slice(1)}</text></g> })}
      </g>
    </svg>
    <div className="map-controls"><button aria-label="Zoom in" disabled={zoom >= 1.8} onClick={() => setZoom(z => Math.min(1.8, z + .2))}><Plus size={17}/></button><button aria-label="Zoom out" disabled={zoom <= .8} onClick={() => setZoom(z => Math.max(.8, z - .2))}><Minus size={17}/></button><button aria-label="Reset map view" onClick={() => setZoom(1)}><RotateCcw size={15}/></button></div>
    <button className={`layer-control ${facilities ? 'on' : ''}`} aria-pressed={facilities} onClick={() => setFacilities(v => !v)}><Layers size={15}/> Hospital records</button>
    <div className="map-route-label"><span className="coral-line"/><div><strong>{selected} → nearest cached facility</strong><span>{baseline ? distance(route?.distance_m) + ' · snapped-node distance' : 'Connect API to calculate a baseline'}</span></div></div>
    <div className="map-attribution"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors · ODbL</a><span>Snapshot {date(data.manifest.download_completed_utc)}</span></div>
    <div className="origin-selector"><span>Sample origin</span><div>{data.origins.map(p => <button key={p.id} aria-pressed={selected === p.id} aria-label={`Select origin ${p.id}`} onClick={() => setSelected(p.id)}>{p.id}</button>)}</div><ArrowRight size={16}/><span className="origin-hint">Select to trace access</span></div>
  </div>
}

export function PageIntro({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) { return <div className="page-intro"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div> }
