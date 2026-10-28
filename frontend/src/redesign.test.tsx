import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { api, atlasSchema, scenarioSchema, environmentSchema } from './api'
import { accessibilitySummary, closureGeometry, matchingSnapshot, routeGeometry } from './features/workspace/spatial'
import App from './App'
vi.mock('./features/workspace/SpatialMap', () => ({ default: () => <div role="img" aria-label="Controlled renderer, not WebGL verification"/> }))
const read = (path:string) => JSON.parse(readFileSync(resolve(path),'utf8').replace(/^\uFEFF/,''))
const atlas=atlasSchema.parse(read('public/data/heidelberg-atlas.json'))
const baseline=read('../evidence/phase5a/baseline-api.json')
const scenario=scenarioSchema.parse(read('../evidence/frontend-redesign/scenario-api.json'))
const environment=environmentSchema.parse(read('../evidence/phase4c-final/live-aj_5_217/deterministic-result.json').result.environment)
function setup(path='/', mode:'ok'|'error'|'mismatch'='ok') {
  const fetch=vi.fn(async (url:string)=>{
    if(url.includes('/analysis/geographic')&&mode==='error')return new Response('unavailable',{status:503})
    const response=url.includes('active-atlas')?atlas:url.includes('/health')?{status:'ok',database:'ok',geographic_cache_present:true,model_cache_present:true}:url.includes('/baseline')?baseline:url.includes('/geographic')?mode==='mismatch'?{...scenario,dataset:{...scenario.dataset,download_completed_utc:'2025-01-01T00:00:00Z'}}:scenario:url.includes('/environment')?environment:[]
    return new Response(JSON.stringify(response))
  })
  vi.stubGlobal('fetch',fetch)
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></QueryClientProvider>)
  return fetch
}
async function runScenario() {
  await screen.findByText('921 m')
  fireEvent.click(screen.getByRole('button',{name:'Disruption lab'}))
  fireEvent.click(screen.getByRole('button',{name:'Analyze disruption'}))
}
describe('geographic integrity',()=>{
  it('sends the selected weather variable to the real environment API contract',async()=>{
    const fetch=vi.fn(async()=>new Response(JSON.stringify(environment)))
    vi.stubGlobal('fetch',fetch)
    await api.environment('2026-10-24T19:55:49Z',undefined,'wind_speed_10m')
    expect(fetch).toHaveBeenCalledWith('/api/analysis/environment',expect.objectContaining({method:'POST',body:JSON.stringify({mode:'cache',variable:'wind_speed_10m',as_of:'2026-10-24T19:55:49Z'})}))
  })
  it('matches equivalent timezone instants and rejects mismatched/invalid snapshots',()=>{
    expect(matchingSnapshot(atlas,baseline.dataset.download_completed_utc)).toBe(true)
    expect(matchingSnapshot(atlas,'2025-01-01T00:00:00Z')).toBe(false)
    expect(matchingSnapshot(atlas,'invalid')).toBe(false)
  })
  it('does not bridge missing graph nodes to fabricate a route',()=>{
    const row=scenario.analysis.baseline[0]
    expect(routeGeometry(atlas,row).features).toHaveLength(1)
    expect(routeGeometry({...atlas,nodes:{}},row).features).toHaveLength(0)
  })
  it('uses actual closure endpoints and removes only previewed reopened segments',()=>{
    const features=closureGeometry(atlas,scenario).features
    expect(new Set(features.map(f=>f.properties?.id)).size).toBe(scenario.analysis.closures.length)
    for(const f of features){
      const c=scenario.analysis.closures.find(c=>c.id===f.properties?.id)!
      const expected=atlas.road_features!.filter(r=>(r.u===c.u&&r.v===c.v)||(r.u===c.v&&r.v===c.u))
      expect(expected.some(r=>JSON.stringify({type:'LineString',coordinates:r.coordinates})===JSON.stringify(f.geometry))).toBe(true)
    }
    expect(closureGeometry(atlas,scenario,[scenario.analysis.closures[0].id]).features.every(f=>f.properties?.id!==scenario.analysis.closures[0].id)).toBe(true)
  })
  it('matches cached minimum directed edge weights to backend route distances',()=>{
    for(const row of [...scenario.analysis.baseline,...scenario.analysis.disrupted]){
      if(row.distance_m===null)continue
      const total=row.path.slice(1).reduce((sum,v,i)=>sum+atlas.edge_routes![`${row.path[i]}/${v}`].length_m,0)
      expect(total).toBeCloseTo(row.distance_m,6)
    }
    expect(routeGeometry({...atlas,edge_routes:{}},scenario.analysis.baseline[0]).features).toHaveLength(0)
  })
  it('keeps disconnected origins out of the reachable mean without hiding their count',()=>{
    const rows=scenario.analysis.baseline.map((r,i)=>({...r,distance_m:i===0?null:100}))
    expect(accessibilitySummary(rows)).toEqual({reachable:8,total:9,mean:100})
    expect(accessibilitySummary(rows.map(r=>({...r,distance_m:null})))).toEqual({reachable:0,total:9,mean:null})
  })
})
describe('actual-data-backed analytical workflow with controlled HTTP',()=>{
  it('makes no automatic analysis POST and previews the computed beneficial pair',async()=>{
    const fetch=setup()
    await screen.findByText('921 m')
    expect(fetch.mock.calls.some(([url])=>url.includes('/geographic')||url.includes('/environment'))).toBe(false)
    await runScenario()
    const best=await screen.findByRole('button',{name:/D1 \+ D2.*433 m saved/})
    expect(await screen.findByRole('heading',{name:'O6 Heidelberg'})).toBeInTheDocument()
    expect(screen.getAllByText('+766 m').length).toBeGreaterThan(0)
    fireEvent.click(best)
    expect(await screen.findByText('Restoration preview')).toBeInTheDocument()
    const actual=scenario.pair_restorations.find(r=>Array.isArray(r.reopened)&&r.reopened.includes('D1')&&r.reopened.includes('D2'))!
    expect(actual.distance_saved_m_for_already_reachable).toBeCloseTo(432.8682130453435)
    expect(screen.getByText('Computed restoration distance')).toBeInTheDocument()
    expect(fetch.mock.calls.filter(([url])=>url.includes('/geographic'))).toHaveLength(1)
    expect(fetch).toHaveBeenCalledWith('/api/analysis/geographic',expect.objectContaining({method:'POST',body:JSON.stringify({selection:'betweenness',count:3})}))
  })
  it('disables duplicate execution while a controlled request is pending',async()=>{
    setup()
    const original=globalThis.fetch
    let finish!:(value:Response)=>void
    const fetch=vi.fn((url:string,options?:RequestInit)=>url.includes('/geographic')?new Promise<Response>(resolve=>{finish=resolve}):original(url,options))
    vi.stubGlobal('fetch',fetch)
    await runScenario()
    expect(await screen.findByRole('button',{name:/Computing scenario/})).toBeDisabled()
    expect(fetch.mock.calls.filter(([url])=>url.includes('/geographic'))).toHaveLength(1)
    finish(new Response(JSON.stringify(scenario)))
    await screen.findByText('Hypothetical disruption')
  })
  it('keeps a valid baseline when analysis fails, with no automatic retry',async()=>{
    const fetch=setup('/','error'); await runScenario()
    expect(await screen.findByText(/Request failed \(503\)/)).toBeInTheDocument()
    expect(screen.getByText('Baseline accessibility')).toBeInTheDocument()
    expect(fetch.mock.calls.filter(([url])=>url.includes('/geographic'))).toHaveLength(1)
  })
  it('blocks a mismatched-snapshot overlay instead of showing false changes',async()=>{
    setup('/','mismatch'); await runScenario()
    expect(await screen.findByText(/Scenario snapshot differs/)).toBeInTheDocument()
    expect(screen.getByText('Baseline accessibility')).toBeInTheDocument()
    expect(screen.queryByText('Hypothetical disruption')).not.toBeInTheDocument()
  })
  it('invalidates the displayed scenario when the requested segment count changes',async()=>{
    setup(); await runScenario(); await screen.findByText('Hypothetical disruption')
    fireEvent.change(screen.getByLabelText('Segments to remove'),{target:{value:'4'}})
    expect(screen.getByText('Baseline accessibility')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Scenario'})).toBeDisabled()
  })
  it('loads real saved environmental values only on demand and exposes individual predictions',async()=>{
    const fetch=setup('/environment')
    expect(screen.getByText('NO PREDICTION LOADED')).toBeInTheDocument()
    expect(fetch.mock.calls.some(([url])=>url.includes('/analysis/environment'))).toBe(false)
    fireEvent.click(screen.getByRole('button',{name:'Load evidence + forecast'}))
    expect(await screen.findByRole('img',{name:/Actual cached environmental/})).toBeInTheDocument()
    const slider=screen.getByLabelText('Inspect forecast hour')
    fireEvent.change(slider,{target:{value:'12'}})
    expect(screen.getByText('FORECAST SAMPLE · HOUR 13')).toBeInTheDocument()
    expect(screen.getByText(environment.forecast.forecast_values[12].toFixed(2),{exact:false})).toBeInTheDocument()
    expect(screen.getByText(/Environmental estimates and forecasts do not establish/)).toBeInTheDocument()
    expect(fetch.mock.calls.filter(([url])=>url.includes('/analysis/environment'))).toHaveLength(1)
  })
})
