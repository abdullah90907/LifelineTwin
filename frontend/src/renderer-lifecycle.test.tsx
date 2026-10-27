import { StrictMode } from 'react'
import { act, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { atlasSchema } from './api'
const state=vi.hoisted(()=>({instances:[] as any[]}))
vi.mock('maplibre-gl',()=>{
  class FakeMap {
    canvas=document.createElement('canvas'); callbacks:Record<string,Function>={}; sources:Record<string,any>={}
    constructor(){state.instances.push(this)}
    on(name:string,...args:any[]){this.callbacks[name]=args.at(-1);return this}
    addControl(){return this} getCanvas(){return this.canvas} resize(){return this} fitBounds(){return this}
    addSource(id:string){this.sources[id]={setData:vi.fn()};return this} getSource(id:string){return this.sources[id]}
    addLayer(){return this} setLayoutProperty(){return this}
    remove(){this.canvas.dispatchEvent(new Event('webglcontextlost'))}
  }
  class Marker {setLngLat(){return this}addTo(){return this}remove(){}}
  class Popup {setLngLat(){return this}setText(){return this}addTo(){return this}remove(){}}
  return {Map:FakeMap,Marker,Popup,NavigationControl:class{},ScaleControl:class{},setWorkerUrl:vi.fn(),setWorkerCount:vi.fn()}
})
import SpatialMap from './features/workspace/SpatialMap'
const atlas=atlasSchema.parse(JSON.parse(readFileSync(resolve('public/data/heidelberg-atlas.json'),'utf8')))
const props={atlas,selected:'O5',reopened:[],showRoads:true,showOrigins:true,showFacilities:true,onOrigin:vi.fn(),onFacility:vi.fn()}
beforeEach(()=>{state.instances=[];vi.stubGlobal('ResizeObserver',class{observe(){}disconnect(){}})})
describe('renderer lifecycle with a controlled GPU adapter, not live WebGL evidence',()=>{
  it('does not confuse Strict Mode cleanup context loss with active GPU failure',()=>{
    const {container}=render(<StrictMode><SpatialMap {...props}/></StrictMode>)
    expect(state.instances).toHaveLength(2)
    expect(screen.queryByRole('img',{name:/Compatibility rendering/})).not.toBeInTheDocument()
    act(()=>state.instances[1].callbacks.load())
    expect(container.querySelector('[data-renderer]')).toHaveAttribute('data-renderer','maplibre')
  })
  it('announces an actual active-context loss through the compatibility renderer',()=>{
    const {container}=render(<SpatialMap {...props}/>)
    act(()=>state.instances[0].callbacks.load())
    act(()=>state.instances[0].canvas.dispatchEvent(new Event('webglcontextlost')))
    expect(container.querySelector('[data-renderer]')).toHaveAttribute('data-renderer','compatibility')
    expect(screen.getByRole('img',{name:/Compatibility rendering/})).toBeInTheDocument()
  })
})
