import { useState } from 'react'
import type { Environment } from '../../api'

export default function ForecastChart({ data }: { data: Environment }) {
  const [index, setIndex] = useState(0)
  const obs = data.observations.variables[data.forecast.variable]
  const values = obs.values.slice(-96), forecasts = data.forecast.forecast_values
  const selected = Math.min(index, forecasts.length - 1)
  const finite = [...values, ...forecasts].filter((v): v is number => v !== null)
  const min = Math.min(...finite), max = Math.max(...finite), padding = Math.max(.5,(max-min)*.15)
  const yMin = min-padding, yMax = max+padding, count = values.length+forecasts.length
  const x = (i:number) => 54+i/Math.max(1,count-1)*810
  const y = (v:number) => 254-(v-yMin)/(yMax-yMin)*210
  function path(items:(number|null)[], offset:number) { let pen=false; return items.map((v,i)=>{if(v===null){pen=false;return ''}const d=`${pen?'L':'M'}${x(i+offset)},${y(v)}`;pen=true;return d}).join(' ') }
  const boundary=x(values.length-1)
  return <div className="forecast-chart"><div className="chart-readout"><span>FORECAST SAMPLE · HOUR {selected+1}</span><strong>{forecasts[selected].toFixed(2)} <small>{data.forecast.unit}</small></strong><time>{new Date(data.forecast.forecast_timestamps[selected]).toUTCString()}</time></div>
    <svg viewBox="0 0 900 300" role="img" aria-label="Actual cached environmental estimates and pretrained temperature predictions" onPointerMove={e=>{const rect=e.currentTarget.getBoundingClientRect();const logical=(e.clientX-rect.left)/rect.width*900;setIndex(Math.max(0,Math.min(forecasts.length-1,Math.round((logical-54)/810*(count-1)-values.length))))}}>
      {[0,.25,.5,.75,1].map(v=>{const value=yMin+(yMax-yMin)*v;return <g key={v}><line x1="54" x2="864" y1={y(value)} y2={y(value)} stroke="#263242" strokeDasharray="2 5"/><text x="40" y={y(value)+4} textAnchor="end">{value.toFixed(1)}°</text></g>})}
      <rect x={boundary} y="30" width={864-boundary} height="224" fill="#a88eff" opacity=".035"/>
      <line x1={boundary} x2={boundary} y1="30" y2="254" stroke="#657087" strokeDasharray="4 5"/>
      <text x="58" y="20">CACHED ESTIMATES</text><text x={boundary+15} y="20">PRETRAINED PREDICTION</text>
      <path d={path(values,0)} fill="none" stroke="#52d5c3" strokeWidth="2.5"/>
      <path d={path([values.at(-1)??null,...forecasts],values.length-1)} fill="none" stroke="#baa0ff" strokeWidth="2.5" strokeDasharray="5 3"/>
      <line x1={x(values.length+selected)} x2={x(values.length+selected)} y1="30" y2="254" stroke="#baa0ff" opacity=".4"/>
      <circle cx={x(values.length+selected)} cy={y(forecasts[selected])} r="5" fill="#baa0ff" stroke="#171b2b" strokeWidth="3"/>
      <text x="54" y="282">{new Date(data.observations.timestamps.at(-values.length)!).toLocaleDateString('en-GB',{day:'2-digit',month:'short',timeZone:'UTC'})}</text><text x={boundary} y="282" textAnchor="middle">Context cutoff</text><text x="864" y="282" textAnchor="end">{new Date(data.forecast.forecast_timestamps.at(-1)!).toLocaleDateString('en-GB',{day:'2-digit',month:'short',timeZone:'UTC'})} · UTC</text>
    </svg>
    <div className="forecast-scrubber"><label htmlFor="forecast-hour">Inspect forecast hour</label><input id="forecast-hour" type="range" min="0" max={forecasts.length-1} value={selected} onChange={e=>setIndex(Number(e.target.value))}/><output>{selected+1} / {forecasts.length}</output></div>
  </div>
}
