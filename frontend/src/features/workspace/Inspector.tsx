import { ArrowRight, CircleHelp, GitCompareArrows, Hospital, MapPin, Route, ShieldCheck, Sparkles } from 'lucide-react'
import { distance, ErrorState } from '../../components'
import type { Analysis } from './useAnalysis'

export default function Inspector({ model: m }: { model: Analysis }) {
  const delta = m.base?.distance_m != null && m.active?.distance_m != null ? m.active.distance_m - m.base.distance_m : null
  return <aside className="context-panel" aria-label="Selected origin and analytical evidence">
    <div className="panel-caption"><span>CONTEXT INSPECTOR</span><Sparkles size={13}/></div>
    <div className="context-scroll"><div className="context-object"><span className="object-symbol"><MapPin size={22}/></span><div><span className="toolbar-kicker">SAMPLED GRID ORIGIN</span><h2>{m.selected}{" "}<span>{m.city}</span></h2></div><span className="selection-pip"/></div>
      <div className="context-measure"><span>Nearest-facility access</span><strong>{m.active ? distance(m.active.distance_m) : '—'}</strong><small>{m.view === 'baseline' ? 'Baseline network distance' : m.view === 'restoration' ? 'Computed restoration distance' : 'Computed scenario distance'}</small></div>
      {m.view !== 'baseline' && m.base && m.active && <div className="delta-row"><span>{distance(m.base.distance_m)} baseline</span><ArrowRight size={12}/><strong>{delta === null ? m.base.distance_m === m.active.distance_m ? 'Unreachable in both' : 'Connectivity changed' : `${delta >= 0 ? '+' : ''}${Math.round(delta)} m`}</strong></div>}
      <div className="route-narrative"><div><span className="route-node origin-node"/><span><strong>Origin {m.selected}</strong><small>Snapped to OSM node {m.base?.node ?? '—'}</small></span></div><div className="route-connector"><Route size={13}/><span>{m.active?.path.length ?? '—'} route nodes · distance-weighted</span></div><div><span className="route-node facility-node"><Hospital size={12}/></span><span><strong>{m.selectedFacility?.name ?? (m.active?.distance_m === null ? 'No reachable facility' : 'Facility not selected')}</strong><small>{m.selectedFacility ? `OSM node ${m.selectedFacility.node}` : 'Awaiting analytical result'}</small></span></div></div>
      {m.facility && <p className="context-notice">Map-selected facility details. This selection does not recalculate the nearest-facility route.<button className="text-button" onClick={() => m.setFacility(null)}>Show route destination</button></p>}
      {m.w.baseline.isError && <ErrorState error={m.w.baseline.error} retry={() => void m.w.baseline.refetch()}/>}
      {m.w.baseline.data && m.atlas && !m.baseline && !m.w.baseline.isError && <ErrorState error={new Error('Atlas and baseline snapshots differ. Re-export cached geometry before comparing.')}/>}
      {m.scenario.data && m.atlas && !m.result && <ErrorState error={new Error('Scenario snapshot differs from the displayed map. Result overlay is disabled.')}/>}
      <div className="inspector-divider"/>
      {m.result ? <><div className="panel-section-title"><span>RESTORATION ALTERNATIVES</span><span>{m.allRestorations.length}</span></div><p className="panel-help">Sorted by reconnection, then distance saved. Savings sum origin-metres for already-reachable origins, not an individual route saving.</p><div className="restoration-list">{m.allRestorations.map((r, index) => {
        const ids = Array.isArray(r.reopened) ? r.reopened : [r.reopened]
        return <button key={index} className={m.restoration === r && m.view === 'restoration' ? 'selected' : ''} onClick={() => m.preview(r)}><span className="restoration-rank">{String(index + 1).padStart(2, '0')}</span><span><strong>{ids.join(' + ')}</strong><small>{r.reconnected_origins} reconnected · {Math.round(r.distance_saved_m_for_already_reachable)} m saved</small><em>{ids.map(id => { const c = m.result!.analysis.closures.find(c => c.id === id); return c ? `${c.u} ↔ ${c.v}` : id }).join(' / ')}</em></span><ArrowRight size={12}/></button>
      })}</div></> : <div className="inspector-prompt"><GitCompareArrows size={22}/><h3>From route to resilience.</h3><p>Run a hypothetical disruption to compare access and inspect computed restoration alternatives.</p><button className="text-button" onClick={() => m.setLeftTab('scenario')}>Open disruption lab<ArrowRight size={12}/></button></div>}
      <div className="evidence-footnote"><CircleHelp size={15}/><p>Cached network, snapped nodes, equal-weight origins. Hospital capability and current road conditions are unverified.</p></div>
      {m.result && <details className="source-details"><summary>Analytical limitations</summary>{m.result.limitations.map(v => <p key={v}>{v}</p>)}</details>}
    </div><div className="context-bottom"><ShieldCheck size={13}/><span>Evidence first. Human judgment always.</span></div>
  </aside>
}
