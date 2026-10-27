import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { FileText, ChevronRight, X } from 'lucide-react'
import { api } from '../../api'
import type { Incident } from '../../api'
import { Tag, ErrorState, date } from '../../components'

export function IncidentList({ compact = false }: { compact?: boolean }) {
  const [params, setParams] = useSearchParams()
  const rawOffset = Number(params.get('offset') ?? 0)
  const offset = compact || !Number.isInteger(rawOffset) || rawOffset < 0 ? 0 : Math.min(rawOffset, 100000)
  const query = useQuery({ queryKey: ['incidents', offset], queryFn: ({ signal }) => api.incidents(offset, signal) })
  const [selected, setSelected] = useState<Incident | null>(null)
  const rows = compact ? query.data?.slice(0, 3) : query.data
  return <><div className="incident-panel"><div className="panel-top"><span><span className="status-dot"/>LOCAL RECORDS</span><span>{query.data ? `${rows?.length} shown${compact ? ' · latest' : ''}` : 'SQLite workspace'}</span></div>{query.isPending ? <div className="list-loading" aria-live="polite">Loading local incidents…<div className="skeleton"/></div> : query.isError ? <ErrorState error={query.error} retry={() => void query.refetch()}/> : rows?.length ? <div className="incident-list">{rows.map(incident => <button className="incident-row" key={incident.id} onClick={() => setSelected(incident)}><span className="incident-icon"><FileText size={19}/></span><span className="incident-text"><strong>{incident.title}</strong><span>{date(incident.occurred_at)} · {incident.status}</span></span><Tag tone={incident.kind === 'hypothetical' ? 'coral' : 'muted'}>{incident.kind === 'verified' ? 'Attributed verified' : incident.kind.replace('_', ' ')}</Tag><ChevronRight size={16}/></button>)}</div> : <div className="empty-workspace"><div className="empty-icon"><FileText size={26}/><span>+</span></div><h3>{offset ? 'No more records here.' : 'Room for your next question.'}</h3><p>{offset ? 'Return to an earlier page to review stored incidents.' : 'No incidents are stored in this workspace yet. Your future investigations will start here.'}</p><span className="quiet-label">Real records only. No sample incidents.</span></div>}</div>{!compact && <div className="pagination"><button className="secondary-button" disabled={offset === 0 || query.isPending} onClick={() => setParams({ offset: String(Math.max(0, offset - 12)) })}>Previous</button><span>{query.data?.length ? `Records ${offset + 1}–${offset + query.data.length}` : 'No records'}</span><button className="secondary-button" disabled={query.data?.length !== 12 || query.isPending} onClick={() => setParams({ offset: String(offset + 12) })}>Next</button></div>}{selected && <IncidentDialog incident={selected} close={() => setSelected(null)}/>}</>
}

function IncidentDialog({ incident, close }: { incident: Incident; close: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const history = useQuery({ queryKey: ['history', incident.id], queryFn: ({ signal }) => api.history(incident.id, false, signal) })
  const agent = useQuery({ queryKey: ['agent-history', incident.id], queryFn: ({ signal }) => api.history(incident.id, true, signal) })
  useEffect(() => { const dialog = ref.current; const previous = document.activeElement as HTMLElement; dialog?.showModal(); return () => { dialog?.close(); previous?.focus() } }, [])
  return <dialog ref={ref} className="incident-dialog" onCancel={close} aria-labelledby="incident-title"><div className="dialog-top"><Tag tone="coral">{incident.kind.replace('_', ' ')}</Tag><button className="icon-button" aria-label="Close incident details" onClick={close}><X size={19}/></button></div><h2 id="incident-title">{incident.title}</h2><p className="dialog-description">{incident.description}</p><div className="detail-meta"><span>Status <strong>{incident.status}</strong></span><span>Occurred <strong>{date(incident.occurred_at)}</strong></span><span>Context <strong>{incident.context.latitude.toFixed(4)}, {incident.context.longitude.toFixed(4)}</strong></span></div><p className="quiet-label">“Verified” denotes submitter attribution, not independent certification.</p><h3>Saved investigation history</h3>{[{ label: 'Deterministic analyses', query: history }, { label: 'AI agent investigations', query: agent }].map(({ label, query }) => <div className="history-group" key={label}><h4>{label}</h4>{query.isPending ? <p>Loading history…</p> : query.isError ? <ErrorState error={query.error}/> : !query.data?.length ? <p>No saved investigations.</p> : query.data.map(row => <div className="history-row" key={row.id}><span>{date(row.created_at)}<small>{row.id}</small></span><span>{label === 'Deterministic analyses' && <Link to={`/investigations/${row.id}`} onClick={close}>Inspect evidence →</Link>}</span><Tag tone={row.status === 'completed' ? '' : 'coral'}>{row.status}</Tag></div>)}</div>)}<p className="quiet-label">Up to 20 most recent records per pipeline. Open deterministic records to inspect their full evidence.</p></dialog>
}

