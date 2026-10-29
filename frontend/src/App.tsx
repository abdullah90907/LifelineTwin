import Continuity from './pages/Continuity'
import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { ArrowUpRight, CloudSun, Compass, FolderGit2, Radio, RefreshCw, ScanLine, ShieldCheck } from 'lucide-react'
import { Brand } from './components'
import { useWorkspace } from './hooks/useWorkspace'
import Workspace from './features/workspace/Workspace'
import Environment from './pages/Environment'
import IncidentPage from './pages/Incidents'
import InvestigationPage from './pages/Investigation'

const navigation = [
  { to: '/', name: 'Continuity overview', short: 'Briefing', icon: ShieldCheck },
  { to: '/explore', name: 'Spatial workspace', short: 'Map', icon: Compass },
  { to: '/environment', name: 'Environmental evidence', short: 'Weather', icon: CloudSun },
  { to: '/incidents', name: 'Investigation library', short: 'Records', icon: FolderGit2 },
]
export default function App() {
  const location = useLocation(), workspace = useWorkspace(location.pathname !== "/"), client = useQueryClient()
  const main = useRef<HTMLElement>(null), previous = useRef(location.pathname)
  useEffect(() => { if (previous.current === location.pathname) return; previous.current = location.pathname; main.current?.focus() }, [location.pathname])
  const online = workspace.health.data?.status === 'ok' && !workspace.health.isError
  const pending = workspace.health.isFetching || workspace.baseline.isFetching
  const current = navigation.find(n => n.to === location.pathname)?.name ?? (location.pathname.startsWith('/investigations/') ? 'Investigation evidence' : 'Spatial workspace')
  return <div className="product-shell"><a className="skip-link" href="#main">Skip to content</a>
    <header className="app-header"><Brand/><div className="header-separator"/><div className="header-region"><span>{location.pathname === "/" ? "Houston + West Alabama" : workspace.atlas.data?.manifest.area?.includes("Houston") ? "Houston · TX" : "Heidelberg"}</span><span>/</span>{current}</div><span className="research-mode"><ShieldCheck size={12}/>LOCAL RESEARCH</span><div className="header-connection" aria-live="polite"><span className={`status-dot ${online ? '' : 'offline'}`}/>{workspace.health.isPending ? 'Connecting API' : online ? 'API connected' : 'API unavailable'}</div><button className="icon-button" aria-label="Refresh backend data" disabled={pending} onClick={() => void client.invalidateQueries({ predicate: q => ['health','baseline','incidents','history','agent-history','continuity-regions','continuity-signals','continuity-cases'].includes(String(q.queryKey[0])) })}><RefreshCw size={15} className={pending ? 'spinning' : ''}/></button></header>
    <nav className="app-rail" aria-label="Main navigation"><div className="rail-emblem"><ScanLine size={20}/></div>{navigation.map(({to,name,short,icon:Icon}) => <NavLink key={to} end={to === '/'} to={to} aria-label={name} title={name}><Icon size={20}/><span>{short}</span></NavLink>)}<div className="rail-bottom"><Radio size={17}/><span>LOCAL</span></div></nav>
    <main id="main" ref={main} tabIndex={-1} className="app-main"><Routes><Route path="/" element={<Continuity/>}/><Route path="/explore" element={<Workspace workspace={workspace}/>}/><Route path="/atlas" element={<Navigate replace to="/explore"/>}/><Route path="/environment" element={<Environment/>}/><Route path="/intelligence" element={<Navigate replace to="/environment"/>}/><Route path="/incidents" element={<IncidentPage/>}/><Route path="/investigations/:id" element={<InvestigationPage/>}/><Route path="*" element={<div className="not-found"><span className="toolbar-kicker">OUTSIDE THE WORKSPACE</span><h1>This view doesn’t exist.</h1><Link className="run-analysis" to="/explore">Return to spatial workspace<ArrowUpRight size={15}/></Link></div>}/></Routes></main>
  </div>
}

