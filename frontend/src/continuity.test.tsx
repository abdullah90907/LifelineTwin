import { describe,it,expect,vi } from 'vitest'
import { render,screen,fireEvent,waitFor } from '@testing-library/react'
import { QueryClient,QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Continuity from './pages/Continuity'

const regions=['houston','alabama'].map(id=>({id,name:id==='houston'?'Houston, Texas':'West Alabama',focus:'Controlled test area',ready:true,snapshot_at:'2026-10-29T00:00:00Z',communities:[{id:'place/'+id,name:id+' community'}],facilities:[{id:id+'/hospital',name:id==='houston'?'Houston Methodist Hospital':'DCH Regional Medical Center'}]}))
const feed={status:'available',source_url:'https://example.org/official-source',retrieved_at:'2026-10-29T00:00:00Z'}
function record(region:string){return {id:'saved-'+region,region,created_at:'2026-10-29T00:00:00Z',request:{title:'Exercise: '+region,source:'Controlled planning exercise',observed_at:'2026-10-29T00:00:00Z',evidence_kind:'exercise'},result:{region,region_name:region,computed_at:'2026-10-29T00:00:00Z',verification:'exercise',input_sha256:'a'.repeat(64),summary:{communities_evaluated:1,communities_with_longer_routes:1,communities_newly_disconnected:0,largest_increase_m:1000,population_affected:null},communities:[{id:'place/'+region,name:region+' community',baseline_m:1000,scenario_m:2000,increase_m:1000,newly_disconnected:false,alternative_facility:'Alternative hospital'}],alternatives:[{id:'restore',action:'Restore the facility',kind:'facility_restoration',reconnected_communities:0,communities_with_shorter_routes:1,mean_distance_saved_m:1000,distance_saved_m:1000,assumption:'Requires verification'}],limitations:['Not a population estimate.']}}}
function setup({unavailable=false,create}:{unavailable?:boolean;create?:(body:Record<string,unknown>)=>Promise<Response>}={}){
 const fetch=vi.fn(async(url:string,options?:RequestInit)=>{
  if(options?.method==='POST'){const body=JSON.parse(options.body as string);return create?create(body):new Response(JSON.stringify(record(body.region)))}
  if(url.endsWith('/regions'))return new Response(JSON.stringify(regions))
  if(url.includes('/signals/'))return new Response(JSON.stringify({region:url.split('/').at(-1),coverage:'Reference point only',alerts:{...feed,status:unavailable?'unavailable':'available',data:unavailable?null:[]},weather:{...feed,status:'unavailable',data:null}}))
  return new Response('[]')
 })
 vi.stubGlobal('fetch',fetch)
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter><Continuity/></MemoryRouter></QueryClientProvider>)
 return fetch
}
describe('continuity decision workflow',()=>{
 it('preserves exact regional inputs and exposes a downloadable evidence brief',async()=>{
  const fetch=setup()
  await screen.findByLabelText('Hospital record')
  fireEvent.click(screen.getByRole('button',{name:'Assess access & save brief'}))
  expect(await screen.findByRole('link',{name:'Export brief'})).toHaveAttribute('href','/api/continuity/cases/saved-houston/brief')
  const post=fetch.mock.calls.find(([,options])=>options?.method==='POST')!
  const body=JSON.parse(post[1]!.body as string)
  expect(body.region).toBe('houston');expect(body.unavailable_facilities).toEqual(['houston/hospital']);expect(body.evidence_kind).toBe('exercise')
  expect(screen.getByText(/Affected population is unavailable/)).toBeInTheDocument()
 })
 it('clears an old result when moving to a different region',async()=>{
  setup();await screen.findByLabelText('Hospital record')
  fireEvent.click(screen.getByRole('button',{name:'Assess access & save brief'}));await screen.findByRole('link',{name:'Export brief'})
  fireEvent.click(screen.getByRole('button',{name:/West Alabama.*Tuscaloosa/}))
  await waitFor(()=>expect(screen.getByLabelText('Hospital record')).toHaveValue('alabama/hospital'))
  expect(screen.queryByRole('link',{name:'Export brief'})).not.toBeInTheDocument()
 })
 it('does not turn an unavailable alert feed into zero active alerts',async()=>{
  setup({unavailable:true});await screen.findByLabelText('Hospital record')
  expect(await screen.findByText('Missing alert data does not establish safe conditions.')).toBeInTheDocument()
  expect(screen.queryByText('0 active alerts')).not.toBeInTheDocument()
 })
 it('blocks duplicate writes and automatic replay after an ambiguous response',async()=>{
  let reject!:(reason:Error)=>void
  const fetch=setup({create:()=>new Promise((_resolve,rejection)=>{reject=rejection})})
  await screen.findByLabelText('Hospital record')
  const button=screen.getByRole('button',{name:'Assess access & save brief'})
  fireEvent.click(button);fireEvent.click(button)
  expect(fetch.mock.calls.filter(([,options])=>options?.method==='POST')).toHaveLength(1)
  reject(new Error('Connection interrupted'))
  await screen.findByRole('alert')
  expect(screen.getByRole('button',{name:'Assess access & save brief'})).toBeDisabled()
  expect(fetch.mock.calls.filter(([,options])=>options?.method==='POST')).toHaveLength(1)
 })
})
