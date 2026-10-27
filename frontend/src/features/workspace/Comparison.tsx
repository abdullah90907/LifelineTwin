import type { RouteRow } from '../../api'
import { distance } from '../../components'
export default function Comparison({ before, after, selected, choose, changed }: { before: RouteRow[]; after: RouteRow[]; selected: string; choose: (id: string) => void; changed: boolean }) {
  const max = Math.max(1, ...before.concat(after).map(r => r.distance_m ?? 0))
  if (!before.length) return <p className="comparison-empty">Baseline is unavailable. Connect the API to compare actual network distances.</p>
  return <div className="comparison-grid">{before.map(a => {
    const b = after.find(r => r.id === a.id)
    const delta = a.distance_m !== null && b?.distance_m !== null && b?.distance_m !== undefined ? b.distance_m - a.distance_m : null
    return <button key={a.id} aria-label={`Inspect comparison ${a.id}`} className={selected === a.id ? 'active' : ''} onClick={() => choose(a.id)}><span className="bar-title">{a.id}<span>{changed && delta !== null && delta > 0 ? `+${Math.round(delta)} m` : b?.distance_m === null ? 'No route' : distance(b?.distance_m)}</span></span><span className="chart-track"><i style={{ width: `${(a.distance_m ?? 0) / max * 100}%` }}/></span>{changed && <span className="chart-track after"><i style={{ width: `${(b?.distance_m ?? 0) / max * 100}%` }}/></span>}</button>
  })}</div>
}
