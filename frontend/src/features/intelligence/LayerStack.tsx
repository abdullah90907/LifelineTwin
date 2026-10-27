import { Globe2, Waves, Activity, Sparkles } from 'lucide-react'
import type { Workspace } from '../../hooks/useWorkspace'

export function LayerStack({ workspace: w }: { workspace: Workspace }) {
  const items = [
    { icon: Globe2, title: 'Geographic network', text: 'OSMnx · NetworkX', state: w.health.data?.geographic_cache_present ? 'Cache present' : 'Not confirmed' },
    { icon: Waves, title: 'Environmental signals', text: 'Open-Meteo · cached estimates', state: 'On demand' },
    { icon: Activity, title: 'Pretrained forecasting', text: 'IBM Granite · TinyTimeMixer', state: w.health.data?.model_cache_present ? 'Weights present' : 'Not confirmed' },
    { icon: Sparkles, title: 'AI investigation', text: 'LangGraph · evidence-led tools', state: 'Not invoked' },
  ]
  return <div className="layer-stack">{items.map(({ icon: Icon, title, text, state }) => <div className="layer-row" key={title}><span className="layer-icon"><Icon size={19}/></span><span><strong>{title}</strong><small>{text}</small></span><span className="layer-state">{state}</span></div>)}</div>
}
