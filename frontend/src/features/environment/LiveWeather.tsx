import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { API_BASE, request } from '../../api'

const values = z.object({time:z.string(),temperature_2m:z.number().nullable(),relative_humidity_2m:z.number().nullable(),precipitation:z.number().nullable(),wind_speed_10m:z.number().nullable()})
const schema = z.object({source:z.string(),retrieved_at:z.string(),location:z.string(),current:values,hourly:z.object({time:z.array(z.string()),temperature_2m:z.array(z.number().nullable()),precipitation_probability:z.array(z.number().nullable()),precipitation:z.array(z.number().nullable()),wind_speed_10m:z.array(z.number().nullable())})})
const alertSchema=z.object({retrieved_at:z.string(),alerts:z.array(z.object({event:z.string().nullable(),severity:z.string().nullable(),headline:z.string().nullable(),description:z.string().nullable(),instruction:z.string().nullable(),expires:z.string().nullable()}))})
export default function LiveWeather({compact=false}:{compact?:boolean}) {
  const alerts=useQuery({queryKey:['current-alerts','houston-v1'],queryFn:({signal})=>request('/weather/alerts',alertSchema,signal),retry:false,staleTime:300000,refetchInterval:300000})
  const weather=useQuery({queryKey:['current-weather','houston-v1'],queryFn:({signal})=>request('/weather/current',schema,signal),retry:false,staleTime:300000,refetchInterval:300000})
  const data=weather.data
  const display=(value:number|null|undefined,unit:string)=>value==null?'Unavailable':`${value.toFixed(1)} ${unit}`
  const now=Date.now()
  const hours=data?.hourly.time.map((time,index)=>({time,index})).filter(row=>new Date(row.time+'Z').getTime()>=now).slice(0,12) ?? []
  return <section className={`live-weather ${compact?'compact':''}`} aria-label="Current study-area weather">
    <div className="live-weather-heading"><div><span className="toolbar-kicker">CURRENT WEATHER · {data?.location?.toUpperCase() ?? 'HOUSTON'}</span><h2>{data?display(data.current.temperature_2m,'°C'):'Connecting to Open-Meteo…'}</h2></div><button className="text-button" disabled={weather.isFetching} onClick={()=>void weather.refetch()}>{weather.isFetching?'Updating…':'Refresh weather'}</button></div>
    {weather.isError&&<p role="alert">Current weather unavailable. Check the API connection and retry.</p>}
    <div className="weather-alerts">{alerts.isError?<p>NWS alerts unavailable · <button className="text-button" onClick={()=>void alerts.refetch()}>Retry alerts</button></p>:alerts.data?.alerts.length===0?<p>No active NWS alerts returned for this point.<small> Checked {new Date(alerts.data.retrieved_at).toUTCString()}</small></p>:alerts.data?.alerts.map((alert,index)=><details key={index}><summary>{alert.severity} · {alert.event}</summary><p>{alert.headline}</p><p>{alert.description}</p><p>{alert.instruction}</p><small>Expires {alert.expires}</small></details>)}</div>
    {data&&<><div className="live-weather-metrics"><span>Wind <strong>{display(data.current.wind_speed_10m,'km/h')}</strong></span><span>Rain <strong>{display(data.current.precipitation,'mm')}</strong></span><span>Humidity <strong>{display(data.current.relative_humidity_2m,'%')}</strong></span></div>
    <p className="weather-timestamp">Conditions: {new Date(data.current.time+'Z').toUTCString()} · Fetched: {new Date(data.retrieved_at).toUTCString()}{weather.isError?' · Last successful response':''}</p>
    {!compact&&<div className="weather-outlook"><h3>Next 12 hours</h3><div className="weather-table-scroll"><table><thead><tr><th>UTC</th><th>Temperature</th><th>Rain chance</th><th>Rain</th><th>Wind</th></tr></thead><tbody>{hours.map(({time,index})=><tr key={time}><td>{time.slice(11,16)}</td><td>{display(data.hourly.temperature_2m[index],'°C')}</td><td>{display(data.hourly.precipitation_probability[index],'%')}</td><td>{display(data.hourly.precipitation[index],'mm')}</td><td>{display(data.hourly.wind_speed_10m[index],'km/h')}</td></tr>)}</tbody></table></div></div>}
    <p className="weather-timestamp">Model-derived conditions, refreshed every five minutes. Road impacts below are computed scenarios.</p></>}
    {compact?<Link className="text-button" to="/environment">12-hour outlook and local AI forecasts →</Link>:<a className="text-button" href={`${API_BASE}/weather/current`} target="_blank" rel="noreferrer">Inspect source response →</a>}
  </section>
}
