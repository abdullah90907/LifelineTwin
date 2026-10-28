import { useState } from 'react'
import LiveWeather from '../environment/LiveWeather'
import { ArrowRight, GitCompareArrows, Hospital, Layers3, LoaderCircle, MapPin, Network, Play, RotateCcw, ShieldCheck, SlidersHorizontal, TriangleAlert } from 'lucide-react'
import { date, distance, ErrorState } from '../../components'
import type { Analysis } from './useAnalysis'
import SaveInvestigation from './SaveInvestigation'

export default function Controls({ model: m }: { model: Analysis }) {
  const [roadSearch,setRoadSearch] = useState('')
  const matchingRoads = (m.atlas?.road_features ?? []).filter(road=>road.name?.toLowerCase().includes(roadSearch.toLowerCase())).slice(0,15)
  return <aside className="control-panel" aria-label="Network and scenario controls">
    <div className="panel-caption"><span>WORKSPACE</span><span className="version-code">TX / 01</span></div>
    <h1>{m.city}<span>{m.city === "Houston" ? "Texas Medical Center access" : "Infrastructure network"}</span></h1>
    <div className="scope-label"><span className="status-dot"/>Cached study area <span>{m.city === "Houston" ? "US · TX" : "DE"}</span></div>
    <div className="control-tabs" aria-label="Workspace mode"><button className={m.leftTab === 'network' ? 'active' : ''} onClick={() => m.setLeftTab('network')}><Layers3 size={14}/>Explore</button><button className={m.leftTab === 'scenario' ? 'active' : ''} onClick={() => m.setLeftTab('scenario')}><GitCompareArrows size={14}/>Disruption lab</button></div>
    <LiveWeather compact/><div className="control-scroll"><label className="field-label" htmlFor="road-search">Find a road to test</label><input id="road-search" className="road-search-input" placeholder="Search street names…" value={roadSearch} onChange={event=>setRoadSearch(event.target.value)}/>{roadSearch && <div className="road-search-results">{matchingRoads.length ? matchingRoads.map((road,index)=><button key={index} disabled={m.scenario.isFetching} onClick={()=>m.toggleRoad(road)}>{road.name}<small> · {road.u} ↔ {road.v}</small></button>) : <p className="panel-help">No matching roads in the study area.</p>}</div>}{m.leftTab === 'network' ? <>
      <div className="panel-section-title"><span>VISIBLE LAYERS</span><SlidersHorizontal size={13}/></div>
      {([{ id: 'roads', label: 'Road network', count: m.atlas?.manifest.directed_edges, icon: Network }, { id: 'facilities', label: 'Hospital records', count: m.atlas?.facilities.length, icon: Hospital }, { id: 'origins', label: 'Sample origins', count: m.atlas?.origins.length, icon: MapPin }] as const).map(({ id, label, count, icon: Icon }) => <button className="layer-toggle" key={id} aria-pressed={m.layers[id]} onClick={() => m.setLayers(v => ({ ...v, [id]: !v[id] }))}><Icon size={16}/><span>{label}<small>{count?.toLocaleString() ?? '—'} {id === 'roads' ? 'directed edges' : 'records'}</small></span><span className={`switch ${m.layers[id] ? 'on' : ''}`}/></button>)}
      <div className="panel-section-title origin-title"><span>TRACE ACCESSIBILITY</span><span>{m.before.length || '—'} ORIGINS</span></div>
      <p className="panel-help">Choose a grid origin to follow its route to a nearest cached facility.</p>
      <div className="origin-list">{m.atlas?.origins.map(o => { const r = m.after.find(r => r.id === o.id); return <button key={o.id} aria-label={`Select origin ${o.id}`} aria-pressed={o.id === m.selected} className={o.id === m.selected ? 'selected' : ''} onClick={() => m.chooseOrigin(o.id)}><span className="origin-id">{o.id}</span><span className="origin-mini-route"/><span>{r ? distance(r.distance_m) : 'Awaiting API'}</span><ArrowRight size={12}/></button> })}</div>
      <button className="scenario-invitation" onClick={() => m.setLeftTab('scenario')}><span className="invitation-icon"><GitCompareArrows size={19}/></span><strong>What changes if a road closes?</strong><span>Test a hypothetical disruption<ArrowRight size={14}/></span></button>
    </> : <>
      <div className="scenario-label"><TriangleAlert size={13}/>HYPOTHETICAL SCENARIO</div><h2 className="lab-title">Put the network<br/>under pressure.</h2><p className="panel-help">Choose roads yourself or use the centrality stress test. Measure changed hospital-access routes, detours, and restoration benefits.</p>
      <p className="panel-help">Click a road on the map to select up to six segments. Analyze your selection, or clear it to use the automatic stress test.</p>{m.roads.length > 0 && <div className="scenario-output"><strong>{m.roads.length}/6 selected roads</strong>{m.roads.map(road=><button className="text-button" key={road.id} onClick={()=>m.toggleRoad(road)}>{road.name || `OSM ${road.u} ↔ ${road.v}`} · Remove</button>)}<button className="text-button" onClick={m.clearRoads}>Clear selected roads</button></div>}<label className="field-label" htmlFor="closure-count">Segments to remove</label><select id="closure-count" value={m.count} disabled={m.scenario.isFetching || m.roads.length > 0} onChange={e => m.changeCount(Number(e.target.value))}>{[1,2,3,4,5,6].map(v => <option key={v} value={v}>{v} hypothetical segment{v > 1 ? 's' : ''}</option>)}</select>
      <div className="selection-method"><Network size={16}/><span>{m.roads.length ? "Manual road selection" : "Sampled betweenness"}<small>Computed scenario · not a road-status report</small></span></div>
      <button className="run-analysis" disabled={!m.online || !m.baseline || m.scenario.isFetching} onClick={() => void m.analyze()}>{m.scenario.isFetching ? <LoaderCircle className="spinning" size={15}/> : <Play size={14}/>} {m.scenario.isFetching ? 'Computing scenario…' : 'Analyze disruption'}<ArrowRight size={14}/></button>
      {m.scenario.isError && <ErrorState error={m.scenario.error}/>}
      {m.result && <div className="scenario-output"><div className="panel-section-title"><span>COMPUTED SEGMENTS</span><span>{m.result.analysis.closures.length}</span></div>{m.result.analysis.closures.map(c => <div className="closure-record" key={c.id}><span className="closure-mark"/><span><strong>{c.id} · hypothetical</strong><small>OSM {c.u}<ArrowRight size={9}/>{c.v}</small></span></div>)}<button className="text-button" onClick={m.reset}><RotateCcw size={12}/>Return to baseline</button></div>}
      {m.result && <SaveInvestigation key={JSON.stringify(m.result.analysis.closures)} scenario={m.result}/>}
      <div className="guardrail"><ShieldCheck size={16}/><p>Map previews remain in memory. Create a saved investigation explicitly to preserve evidence. No real closure is asserted.</p></div>
    </>}</div>
    <div className="panel-source"><Layers3 size={16}/><span>OSM snapshot<small>{m.atlas ? date(m.atlas.manifest.download_completed_utc) : 'Loading cached geometry…'}</small></span><span className="source-badge">CACHED</span></div>
  </aside>
}
