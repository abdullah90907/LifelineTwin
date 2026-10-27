import type { FeatureCollection, Geometry, Feature } from 'geojson'
import type { AtlasData, RouteRow, Scenario } from '../../api'

export const collection = (features: Feature[]): FeatureCollection => ({ type: 'FeatureCollection', features })
export function line(coordinates: number[][], properties = {}): Feature {
  return { type: 'Feature', geometry: { type: 'LineString', coordinates }, properties }
}
export function routeGeometry(atlas: AtlasData, row?: RouteRow): FeatureCollection {
  let coordinates = row?.path.map(node => atlas.nodes[String(node)]) ?? []
  // Never silently bridge a missing source node with a fabricated route.
  if (!coordinates.every(Boolean)) return collection([])
  if (atlas.edge_routes && atlas.road_features && row && row.path.length > 1) {
    coordinates = []
    for (let i=1;i<row.path.length;i++) {
      const edge = atlas.edge_routes[`${row.path[i-1]}/${row.path[i]}`]
      const feature = edge && atlas.road_features[edge.feature_index]
      if (!edge || !feature) return collection([])
      const part = edge.reverse ? [...feature.coordinates].reverse() : feature.coordinates
      coordinates.push(...(i===1 ? part : part.slice(1)))
    }
  }
  return collection(coordinates.length > 1 && coordinates.every(Boolean) ? [line(coordinates)] : [])
}
export function closureGeometry(atlas: AtlasData, scenario?: Scenario, reopened: string[] = []): FeatureCollection {
  return collection((scenario?.analysis.closures ?? []).filter(c => !reopened.includes(c.id)).flatMap(c => {
    const features = atlas.road_features?.filter(f => (f.u===c.u&&f.v===c.v)||(f.u===c.v&&f.v===c.u))
    if (features) return features.map(f=>line(f.coordinates,{id:c.id,u:c.u,v:c.v}))
    const a = atlas.nodes[String(c.u)], b = atlas.nodes[String(c.v)]
    return a && b ? [line([a, b], { id: c.id, u: c.u, v: c.v })] : []
  }))
}
export function places(atlas: AtlasData, type: 'origins' | 'facilities'): FeatureCollection<Geometry> {
  return collection(atlas[type].map(p => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [p.lon, p.lat] }, properties: { id: p.id, node: p.node, label: p.name ?? p.id } })))
}
export function accessibilitySummary(rows: RouteRow[]) {
  const reachable = rows.filter(r => r.distance_m !== null)
  return { reachable: reachable.length, total: rows.length, mean: reachable.length ? reachable.reduce((sum, r) => sum + r.distance_m!, 0) / reachable.length : null }
}
export function matchingSnapshot(atlas: AtlasData, snapshot?: string | { download_completed_utc: string; sha256?: Record<string,string> }) {
  const expected = Date.parse(atlas.manifest.download_completed_utc)
  const returned = snapshot ? Date.parse(typeof snapshot==='string' ? snapshot : snapshot.download_completed_utc) : NaN
  const expectedHash=atlas.manifest.sha256?.['roads.graphml']
  const hashMatches=typeof snapshot==='string'||!expectedHash||snapshot?.sha256?.['roads.graphml']===expectedHash
  return hashMatches && Number.isFinite(expected) && Number.isFinite(returned) && expected === returned
}
