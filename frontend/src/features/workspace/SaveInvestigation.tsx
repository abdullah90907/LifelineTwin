import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api, type Scenario } from '../../api'

export default function SaveInvestigation({ scenario }: { scenario: Scenario }) {
  const [title, setTitle] = useState('Hypothetical Heidelberg access disruption')
  const [asOf, setAsOf] = useState('2026-10-24T19:55:49Z')
  const [state, setState] = useState<'ready' | 'running' | 'failed'>('ready')
  const [error, setError] = useState(''), [incidentId, setIncidentId] = useState<string>()
  const lock = useRef(false), navigate = useNavigate(), client = useQueryClient()
  async function save() {
    if (lock.current) return
    lock.current = true; setState('running')
    try {
      const incident = await api.createIncident(title.trim(), new Date(asOf).toISOString())
      setIncidentId(incident.id)
      await client.invalidateQueries({ queryKey: ['incidents'] })
      const result = await api.investigate(incident.id, new Date(asOf).toISOString(), scenario.analysis.closures)
      navigate(`/investigations/${result.id}`)
    } catch (e) {
      setState('failed'); setError(e instanceof Error ? e.message : 'Investigation failed.')
      // A lost response may already have been committed. Never automatically repeat a write.
    }
  }
  return <section className="save-investigation"><span className="toolbar-kicker">TAKE THE NEXT STEP</span><h3>Investigate & preserve</h3><p>Combine these exact OSM segments with cached environmental evidence and a local pretrained forecast. Save the explanation to SQLite.</p><label htmlFor="investigation-title">Investigation title</label><input id="investigation-title" value={title} maxLength={200} disabled={state !== 'ready'} onChange={e => setTitle(e.target.value)}/><label htmlFor="investigation-cutoff">Historical evidence cutoff (UTC)</label><input id="investigation-cutoff" value={asOf} disabled={state !== 'ready'} onChange={e => setAsOf(e.target.value)}/><small>Default matches the existing October 24 cached demonstration; this is a historical replay.</small><button className="run-analysis" disabled={state !== 'ready' || !title.trim() || !Number.isFinite(Date.parse(asOf)) || !/(Z|[+-]\d{2}:\d{2})$/.test(asOf)} onClick={() => void save()}>{state === 'running' ? 'Computing & saving…' : 'Create saved investigation'}</button><small>Deterministic analytical pipeline · no hosted LLM request. Allow time for local TTM inference.</small>{state === 'failed' && <div role="alert"><p>{error}</p><p>Automatic retries are disabled to avoid duplicate writes. Inspect the library before starting another investigation.{incidentId && ` Created incident: ${incidentId}`}</p><Link to="/incidents">Review saved records →</Link></div>}</section>
}
