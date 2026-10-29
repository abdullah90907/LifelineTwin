import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { api, atlasSchema, baselineSchema, request, healthSchema } from './api'
import { NetworkMap, distance } from './components'
import App from './App'
vi.mock('./features/workspace/SpatialMap', () => ({ default: () => <div role="img" aria-label="Cached Heidelberg controlled test renderer"/> }))

const atlas = atlasSchema.parse(JSON.parse(readFileSync(resolve('public/data/heidelberg-atlas.json'), 'utf8')))
const baseline = baselineSchema.parse(JSON.parse(readFileSync(resolve('../evidence/phase5a/baseline-api.json'), 'utf8').replace(/^\uFEFF/, '')))
const health = { status: 'ok', database: 'ok', geographic_cache_present: true, model_cache_present: true }
function mockApi(offline = false) {
  const fetch = vi.fn(async (url: string) => {
    if (url.includes('active-atlas.json')) return new Response(JSON.stringify(atlas))
    if (offline) return new Response('unavailable', { status: 503 })
    const data = url.includes('/health') ? health : url.includes('/baseline') ? baseline : []
    return new Response(JSON.stringify(data))
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}
function app(path = '/explore') { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></QueryClientProvider>) }

describe('typed API boundary', () => {
  it('rejects incompatible data instead of substituting results', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ status: 'ok' }))))
    await expect(request('/health', healthSchema)).rejects.toThrow('expected API contract')
  })
  it('reports network failures without exposing raw errors', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('sensitive server detail') }))
    await expect(api.health()).rejects.toThrow('Backend unavailable')
  })
  it('passes abort signals and uses the same-origin proxy', async () => {
    const fetch = mockApi(); const controller = new AbortController()
    await api.health(controller.signal)
    expect(fetch).toHaveBeenCalledWith('/api/health', expect.objectContaining({ signal: controller.signal }))
  })
  it('handles invalid JSON responses', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<html>not JSON</html>')))
    await expect(api.health()).rejects.toThrow('unreadable response')
  })
})
describe('real cached atlas and reusable map', () => {
  it('preserves dataset identity and renders all original origin choices', () => {
    expect(atlas.manifest.nodes).toBe(1060); expect(atlas.manifest.directed_edges).toBe(2331)
    render(<NetworkMap data={atlas} baseline={baseline}/>)
    expect(screen.getAllByRole('button', { name: /Select origin/ })).toHaveLength(atlas.origins.length)
    expect(screen.getByText(/885 m/)).toBeInTheDocument()
  })
  it('selects a real origin and displays its exact computed route distance', () => {
    render(<NetworkMap data={atlas} baseline={baseline}/>)
    fireEvent.click(screen.getByRole('button', { name: 'Select origin O1' }))
    expect(screen.getByRole('button', { name: 'Select origin O1' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText(`${distance(baseline.analysis.baseline.find(v => v.id === 'O1')!.distance_m)} · snapped-node distance`)).toBeInTheDocument()
  })
  it('toggles hospital records and bounds zoom with a working reset', () => {
    render(<NetworkMap data={atlas}/>)
    const layer = screen.getByRole('button', { name: 'Hospital records' })
    fireEvent.click(layer); expect(layer).toHaveAttribute('aria-pressed', 'false')
    const zoom = screen.getByRole('button', { name: 'Zoom in' })
    for (let i = 0; i < 7; i++) fireEvent.click(zoom)
    expect(zoom).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Reset map view' }))
    expect(zoom).not.toBeDisabled()
  })
})
describe('application foundation', () => {
  it('loads actual baseline data and keeps empty incidents honest', async () => {
    const fetch = mockApi(); app()
    expect(await screen.findByText('API connected')).toBeInTheDocument()
    expect(await screen.findByText('921 m')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Investigation library' }))
    expect(await screen.findByText('Room for your next question.')).toBeInTheDocument()
    expect(fetch.mock.calls.every(([url]) => !url.includes('agent-investigations') && !url.includes('/environment'))).toBe(true)
  })
  it('navigates to each analytical module with a single active destination', async () => {
    mockApi(); app()
    fireEvent.click(screen.getByRole('link', { name: 'Environmental evidence' }))
    expect(await screen.findByRole('heading', { name: 'Signals, not assumptions.' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Investigation library' }))
    expect(await screen.findByRole('heading', { name: 'Investigation library' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Investigation library' })).toHaveAttribute('aria-current', 'page')
  })
  it('retains cached geography when the API is unavailable and offers retry', async () => {
    mockApi(true); app()
    expect(await screen.findByText('API unavailable')).toBeInTheDocument()
    expect(await screen.findByRole('img', { name: /Cached Heidelberg/ })).toBeInTheDocument()
    expect(await screen.findAllByText(/Request failed \(503\)/)).not.toHaveLength(0)
    expect(screen.queryByText('921 m')).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Retry/ }).length).toBeGreaterThan(0)
  })
  it('supports direct route entry and a recoverable missing page', async () => {
    mockApi(); app('/missing')
    expect(screen.getByRole('heading', { name: 'This view doesn’t exist.' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: /Return to spatial workspace/ }))
    await waitFor(() => expect(screen.getByRole('heading', { name: /Heidelberg Infrastructure network/ })).toBeInTheDocument())
  })
  it('retrieves both saved histories without executing an investigation', async () => {
    const id = '11111111-1111-4111-8111-111111111111'
    const calls: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      calls.push(url)
      const value = url.includes('active-atlas') ? atlas : url.includes('/health') ? health : url.includes('/baseline') ? baseline : url.includes('/agent-investigations') ? [{ id: 'test-agent-history', status: 'limited', created_at: '2026-10-24T00:00:00Z' }] : url.includes('/investigations') ? [] : [{ id, title: 'TEST ONLY record', description: '<script>escaped test text</script>', kind: 'hypothetical', status: 'open', occurred_at: '2026-10-24T00:00:00Z', created_at: '2026-10-24T00:00:00Z', context: { latitude: 49.415, longitude: 8.6775 } }]
      return new Response(JSON.stringify(value))
    }))
    app('/incidents')
    fireEvent.click(await screen.findByRole('button', { name: /TEST ONLY record/ }))
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(await screen.findByText('limited')).toBeInTheDocument()
    expect(calls).toContain(`/api/incidents/${id}/investigations?limit=20`)
    expect(calls).toContain(`/api/incidents/${id}/agent-investigations?limit=20`)
    expect(screen.getByText('<script>escaped test text</script>')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Close incident details' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

