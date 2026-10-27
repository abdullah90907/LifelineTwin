import { lazy, Suspense } from 'react'
import { ChevronDown, ChevronUp, GitCompareArrows, TriangleAlert } from 'lucide-react'
import type { Workspace as WorkspaceData } from '../../hooks/useWorkspace'
import { distance, ErrorState } from '../../components'
import { useAnalysis } from './useAnalysis'
import Controls from './Controls'
import Inspector from './Inspector'
import Comparison from './Comparison'
const SpatialMap = lazy(() => import('./SpatialMap'))

export default function Workspace({ workspace: w }: { workspace: WorkspaceData }) {
  const m = useAnalysis(w)
  return <div className="analysis-workspace">
    <Controls model={m}/>
    <section className="map-workspace" aria-label="Geographic analytical workspace">
      <div className="map-toolbar"><div><span className="toolbar-kicker">SPATIAL EXPLORER</span><strong>{m.view === 'baseline' ? 'Baseline accessibility' : m.view === 'restoration' ? 'Restoration preview' : 'Hypothetical disruption'}</strong></div><div className="view-switch"><button aria-pressed={m.view === 'baseline'} onClick={m.reset}>Baseline</button><button disabled={!m.result} aria-pressed={m.view !== 'baseline'} onClick={() => m.setView('scenario')}>Scenario{m.result && <span/>}</button></div></div>
      <div className="map-stage">{m.atlas ? <Suspense fallback={<div className="map-state">Loading geospatial renderer…</div>}><SpatialMap atlas={m.atlas} selected={m.selected} baseline={m.base} active={m.view === 'baseline' ? undefined : m.active} scenario={m.view === 'baseline' ? undefined : m.result} reopened={m.reopened} showRoads={m.layers.roads} showFacilities={m.layers.facilities} showOrigins={m.layers.origins} onOrigin={m.chooseOrigin} onFacility={m.setFacility}/></Suspense> : w.atlas.isError ? <ErrorState error={w.atlas.error} retry={() => void w.atlas.refetch()}/> : <div className="map-state">Loading verified cached geometry…</div>}
        <div className="map-readout"><span className="readout-label"><span className="live-square"/>{m.view === 'baseline' ? 'BASELINE NETWORK' : m.view === 'restoration' ? 'RESTORATION PREVIEW' : 'HYPOTHETICAL NETWORK'}</span><div><span><b>{m.baseline ? `${m.stats.reachable}/${m.stats.total}` : '—'}</b> origins connected</span><span className="readout-divider"/><span><b>{m.baseline ? distance(m.stats.mean) : '—'}</b> mean reachable distance</span></div></div>
        {m.view !== 'baseline' && <div className="scenario-ribbon"><TriangleAlert size={12}/>{m.result?.analysis.closures.length ?? 0} modeled closures · {m.reopened.length ? `${m.reopened.length} reopened in preview` : 'not verified road conditions'}</div>}
        <div className="map-legend"><span><i className="legend-stroke baseline-stroke"/>Baseline route</span>{m.view !== 'baseline' && <span><i className="legend-stroke scenario-stroke"/>Scenario route</span>}<span><i className="facility-square"/>Hospital record</span></div>
      </div>
      <div className={`comparison-tray ${m.compare ? 'open' : ''}`}><button className="tray-heading" aria-expanded={m.compare} onClick={() => m.setCompare(!m.compare)}><span><GitCompareArrows size={15}/>Accessibility comparison<small>{m.view === 'baseline' ? 'Baseline · all sampled origins' : 'Baseline vs ' + (m.view === 'restoration' ? 'restoration' : 'disruption')}</small></span>{m.compare ? <ChevronDown size={15}/> : <ChevronUp size={15}/>}</button>{m.compare && <Comparison before={m.before} after={m.after} selected={m.selected} choose={m.chooseOrigin} changed={m.view !== 'baseline'}/>}</div>
    </section>
    <Inspector model={m}/>
  </div>
}
