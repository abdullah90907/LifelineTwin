import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { api, type Restoration } from '../../api'
import type { Workspace } from '../../hooks/useWorkspace'
import { accessibilitySummary, matchingSnapshot } from './spatial'

export function useAnalysis(w: Workspace) {
  const [params, setParams] = useSearchParams()
  const selected = w.atlas.data?.origins.some(p => p.id === params.get('origin')) ? params.get('origin')! : 'O5'
  const [leftTab, setLeftTab] = useState<'network' | 'scenario'>('network')
  const [count, setCount] = useState(3)
  const [view, setView] = useState<'baseline' | 'scenario' | 'restoration'>('baseline')
  const [restoration, setRestoration] = useState<Restoration | null>(null)
  const [facility, setFacility] = useState<string | null>(null)
  const [layers, setLayers] = useState({ roads: true, origins: true, facilities: true })
  const [compare, setCompare] = useState(true)
  const [roads,setRoads] = useState<{id:string;u:number;v:number;name?:string}[]>([])
  const scenario = useQuery({ queryKey: ['scenario', count, roads], queryFn: ({ signal }) => roads.length ? api.providedScenario(roads.map(({id,u,v})=>({id,u,v})),signal) : api.scenario(count, signal), enabled: false, staleTime: Infinity, retry: false })
  const atlas = w.atlas.data
  const baseline = !w.baseline.isError && w.baseline.data && atlas && matchingSnapshot(atlas, w.baseline.data.dataset) ? w.baseline.data : undefined
  const result = scenario.data && atlas && matchingSnapshot(atlas, scenario.data.dataset) ? scenario.data : undefined
  const before = baseline?.analysis.baseline ?? []
  const after = view === 'restoration' && restoration ? restoration.accessibility : view === 'scenario' && result ? result.analysis.disrupted : before
  const base = before.find(r => r.id === selected), active = after.find(r => r.id === selected)
  const reopened = view === 'restoration' && restoration ? (Array.isArray(restoration.reopened) ? restoration.reopened : [restoration.reopened]) : []
  const stats = accessibilitySummary(after)
  const allRestorations = result ? [...result.analysis.restorations, ...result.pair_restorations].sort((a,b) => b.reconnected_origins-a.reconnected_origins || b.distance_saved_m_for_already_reachable-a.distance_saved_m_for_already_reachable) : []
  const selectedFacility = atlas?.facilities.find(f => f.id === facility) ?? atlas?.facilities.find(f => f.node === active?.facility_node)
  const online = w.health.data?.status === 'ok' && !w.health.isError
  function chooseOrigin(id: string) { setParams({ origin: id }, { replace: true }); setFacility(null) }
  async function analyze() {
    const answer = await scenario.refetch()
    if (answer.isSuccess && atlas && matchingSnapshot(atlas, answer.data.dataset)) {
      setView('scenario'); setRestoration(null); setCompare(true)
      const impacted = [...answer.data.analysis.changes].filter(r => r.newly_disconnected || (r.increase_m ?? 0)>0)
        .sort((a,b) => Number(b.newly_disconnected)-Number(a.newly_disconnected) || (b.increase_m ?? 0)-(a.increase_m ?? 0))
      if (impacted[0]) chooseOrigin(impacted[0].id)
    }
  }
  function preview(r: Restoration) { setRestoration(r); setView('restoration'); setCompare(true) }
  function changeCount(n: number) { setCount(n); setView('baseline'); setRestoration(null) }
  function reset() { setView('baseline'); setRestoration(null) }
  function toggleRoad(road:{u:number;v:number;name?:string}) {
    if (scenario.isFetching) return
    const id = `road-${Math.min(road.u,road.v)}-${Math.max(road.u,road.v)}`
    setRoads(previous=>previous.some(r=>r.id===id) ? previous.filter(r=>r.id!==id) : previous.length<6 ? [...previous,{...road,id}] : previous)
    setLeftTab('scenario'); reset()
  }
  function clearRoads() { if (!scenario.isFetching) {setRoads([]); reset()} }
  return { city: atlas?.manifest.area?.includes("Houston") ? "Houston" : "Heidelberg", w, roads, toggleRoad, clearRoads, selected, chooseOrigin, leftTab, setLeftTab, count, changeCount, view, setView, restoration, facility, setFacility, layers, setLayers, compare, setCompare, scenario, atlas, baseline, result, before, after, base, active, reopened, stats, allRestorations, selectedFacility, online, analyze, preview, reset }
}
export type Analysis = ReturnType<typeof useAnalysis>
