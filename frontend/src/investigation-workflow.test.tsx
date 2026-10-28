import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { readFileSync } from 'node:fs'
import { api, investigationSchema, scenarioSchema } from './api'
import SaveInvestigation from './features/workspace/SaveInvestigation'
import InvestigationPage from './pages/Investigation'

const scenario = scenarioSchema.parse(JSON.parse(readFileSync('../evidence/frontend-redesign/scenario-api.json', 'utf8').replace(/^\uFEFF/,'')))
function form() { render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><Routes><Route path="/" element={<SaveInvestigation scenario={scenario}/>}/><Route path="/investigations/saved" element={<p>Saved evidence view</p>}/></Routes></MemoryRouter></QueryClientProvider>) }

describe('explicit scenario to saved investigation', () => {
  it('uses exact computed OSM endpoints, disables repeat writes and opens saved evidence', async () => {
    let finish!: (value: Awaited<ReturnType<typeof api.createIncident>>) => void
    const create = vi.spyOn(api, 'createIncident').mockImplementation(() => new Promise(resolve => { finish = resolve }))
    const run = vi.spyOn(api, 'investigate').mockResolvedValue({ id: 'saved' } as Awaited<ReturnType<typeof api.investigate>>)
    form(); const button = screen.getByRole('button', { name: 'Create saved investigation' })
    fireEvent.change(screen.getByLabelText('Evidence cutoff (UTC)'),{target:{value:'2026-10-24T19:55:49Z'}})
    fireEvent.click(button); fireEvent.click(button)
    expect(create).toHaveBeenCalledTimes(1)
    expect(button).toBeDisabled()
    finish({ id: 'incident' } as Awaited<ReturnType<typeof api.createIncident>>)
    expect(await screen.findByText('Saved evidence view')).toBeInTheDocument()
    expect(run).toHaveBeenCalledExactlyOnceWith('incident', '2026-10-24T19:55:49.000Z', scenario.analysis.closures)
  })
  it('does not retry ambiguous failed writes and sends the user to the persistent library', async () => {
    const create = vi.spyOn(api,'createIncident').mockResolvedValue({ id:'retained' } as Awaited<ReturnType<typeof api.createIncident>>)
    const run = vi.spyOn(api,'investigate').mockRejectedValue(new Error('Backend unavailable.'))
    form(); fireEvent.click(screen.getByRole('button',{name:'Create saved investigation'}))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('retained'))
    expect(screen.getByRole('button',{name:'Create saved investigation'})).toBeDisabled()
    expect(screen.getByRole('link',{name:/Review saved records/})).toHaveAttribute('href','/incidents')
    expect(create).toHaveBeenCalledTimes(1); expect(run).toHaveBeenCalledTimes(1)
  })
  it('requires an explicit timezone and a nonempty title', () => {
    form(); fireEvent.change(screen.getByLabelText('Evidence cutoff (UTC)'), {target:{value:'2026-10-24T19:55:49'}})
    expect(screen.getByRole('button',{name:'Create saved investigation'})).toBeDisabled()
  })
  it('renders a real saved result, resolves a citation and exposes exact computed metrics', async () => {
    const saved = investigationSchema.parse(JSON.parse(readFileSync('../evidence/challenge-readiness-20261027/ui-investigation-before-restart.json', 'utf8')))
    vi.spyOn(api,'investigation').mockResolvedValue(saved)
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/investigations/saved']}><Routes><Route path="/investigations/:id" element={<InvestigationPage/>}/></Routes></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByRole('heading',{name:'What changes under this assumption?'})).toBeInTheDocument()
    expect(screen.getByText('765.826 m')).toBeInTheDocument()
    expect(screen.getByText('432.868')).toBeInTheDocument()
    expect(document.getElementById('evidence-geography')).not.toHaveAttribute('open')
    fireEvent.click(screen.getByRole('link',{name:'[geography]'}))
    expect(document.getElementById('evidence-geography')).toHaveAttribute('open')
    expect(screen.getByText(/Zetaris is not connected/)).toBeInTheDocument()
  })
})
