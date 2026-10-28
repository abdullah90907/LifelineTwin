import { z } from 'zod'
const coordinate = z.tuple([z.number(), z.number()])
const place = z.object({ id: z.string(), node: z.number(), lat: z.number(), lon: z.number(), name: z.string().optional() })
export const atlasSchema = z.object({ manifest: z.object({ area: z.string().optional(), nodes: z.number(), directed_edges: z.number(), download_completed_utc: z.string(), sha256: z.record(z.string(), z.string()).optional(), attribution: z.string(), bbox_wsen: z.array(z.number()) }), roads: z.array(z.array(coordinate)), nodes: z.record(z.string(), coordinate), origins: z.array(place), facilities: z.array(place), road_features: z.array(z.object({ u: z.number(), v: z.number(), kind: z.string(), name: z.string().optional(), coordinates: z.array(coordinate) })).optional(), edge_routes: z.record(z.string(), z.object({ feature_index: z.number().int(), reverse: z.boolean(), length_m: z.number() })).optional() })
export const healthSchema = z.object({ status: z.string(), database: z.string(), geographic_cache_present: z.boolean(), model_cache_present: z.boolean() })
export const incidentSchema = z.object({ id: z.string(), title: z.string(), description: z.string(), kind: z.enum(['verified', 'user_reported', 'hypothetical']), status: z.enum(['open', 'investigating', 'resolved']), occurred_at: z.string(), created_at: z.string(), context: z.object({ latitude: z.number(), longitude: z.number() }) })
export const baselineSchema = z.object({ analysis: z.object({ baseline: z.array(z.object({ id: z.string(), node: z.number(), distance_m: z.number().nullable(), facility_node: z.number().nullable(), path: z.array(z.number()) })) }), limitations: z.array(z.string()), dataset: z.object({ download_completed_utc: z.string(), sha256: z.record(z.string(), z.string()).optional() }) })
const historySchema = z.array(z.object({ id: z.string(), status: z.string(), created_at: z.string(), error: z.string().nullable().optional() }))
export type AtlasData = z.infer<typeof atlasSchema>
export type Baseline = z.infer<typeof baselineSchema>
export type Incident = z.infer<typeof incidentSchema>
const routeSchema = baselineSchema.shape.analysis.shape.baseline.element
const restorationSchema = z.object({ reopened: z.union([z.string(), z.array(z.string())]), reconnected_origins: z.number(), distance_saved_m_for_already_reachable: z.number(), accessibility: z.array(routeSchema) })
export const scenarioSchema = z.object({ scenario_type: z.literal('hypothetical'), dataset: baselineSchema.shape.dataset,
  analysis: z.object({ baseline: z.array(routeSchema), disrupted: z.array(routeSchema), closures: z.array(z.object({ id: z.string(), u: z.number(), v: z.number(), name: z.string().optional() })),
    changes: z.array(z.object({ id: z.string(), baseline_m: z.number().nullable(), scenario_m: z.number().nullable(), increase_m: z.number().nullable(), newly_disconnected: z.boolean() })), restorations: z.array(restorationSchema) }),
  pair_restorations: z.array(restorationSchema), limitations: z.array(z.string()) })
export type Scenario = z.infer<typeof scenarioSchema>
export type RouteRow = z.infer<typeof routeSchema>
export type Restoration = z.infer<typeof restorationSchema>
export const environmentSchema = z.object({ observations: z.object({ source: z.string(), retrieved_utc: z.string(), timestamps: z.array(z.string()), n_hours: z.number(), variables: z.record(z.string(), z.object({ unit: z.string(), values: z.array(z.number().nullable()) })) }),
  forecast: z.object({ model_id: z.string(), model_revision: z.string(), variable: z.string(), unit: z.string(), forecast_horizon_hours: z.number(), context_length_hours: z.number(), forecast_timestamps: z.array(z.string()), forecast_values: z.array(z.number()) }),
  provenance: z.object({ context_cutoff_utc: z.string(), excluded_future_hours: z.number(), product_type: z.string(), snapshot_file: z.string().nullable(), weather_implies_road_closure: z.literal(false) }), limitations: z.array(z.string()) })
export type Environment = z.infer<typeof environmentSchema>
export const investigationSchema = z.object({ id: z.string(), incident_id: z.string(), status: z.enum(['completed', 'failed']), created_at: z.string(), error: z.string().nullable(), result: z.object({
  pipeline: z.literal('deterministic_tools_phase4a'), incident_snapshot: incidentSchema, geography: scenarioSchema,
  environment: environmentSchema, evidence: z.array(z.object({ id: z.string() }).passthrough()),
  assumptions: z.array(z.string()), limitations: z.array(z.string()), recommendations: z.array(z.object({ action: z.string(), evidence_refs: z.array(z.string()), conditional: z.boolean() })),
  scenario_memory: z.object({ status: z.string(), engine: z.string(), reason: z.string().optional(), roads: z.array(z.object({ segment_id: z.string(), u: z.number(), v: z.number(), projected_status: z.string() }).passthrough()).optional() }).passthrough().nullable().optional(),
}).nullable() })
export type Investigation = z.infer<typeof investigationSchema>

export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); this.name = 'ApiError' }
}
export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'
export async function request<T>(path: string, schema: z.ZodType<T>, signal?: AbortSignal, local = false, payload?: unknown): Promise<T> {
  let response: Response
  try { response = await fetch(local ? path : `${API_BASE}${path}`, { signal, headers: { Accept: 'application/json', ...(payload === undefined ? {} : { 'Content-Type': 'application/json' }) }, ...(payload === undefined ? {} : { method: 'POST', body: JSON.stringify(payload) }) }) }
  catch (error) { if (signal?.aborted) throw error; throw new ApiError('Backend unavailable. Start the local API, then retry.') }
  if (!response.ok) throw new ApiError(`Request failed (${response.status}). No substitute data is shown.`, response.status)
  let value: unknown
  try { value = await response.json() } catch { throw new ApiError('The server returned an unreadable response.') }
  const result = schema.safeParse(value)
  if (!result.success) throw new ApiError('The response does not match the expected API contract.')
  return result.data
}
export const api = {
  providedScenario: (closures: {id: string; u: number; v: number}[], signal?: AbortSignal) => request('/analysis/geographic', scenarioSchema, signal, false, { selection: 'provided', closures }),
  health: (signal?: AbortSignal) => request('/health', healthSchema, signal),
  atlas: (signal?: AbortSignal) => request('/data/active-atlas.json', atlasSchema, signal, true),
  baseline: (signal?: AbortSignal) => request('/analysis/baseline', baselineSchema, signal),
  scenario: (count: number, signal?: AbortSignal) => request('/analysis/geographic', scenarioSchema, signal, false, { selection: 'betweenness', count }),
  environment: (asOf: string, signal?: AbortSignal, variable = 'temperature_2m') => request('/analysis/environment', environmentSchema, signal, false, { mode: 'cache', variable, as_of: asOf }),
  incidents: (offset: number, signal?: AbortSignal) => request(`/incidents?limit=12&offset=${offset}`, z.array(incidentSchema), signal),
  history: (id: string, agent: boolean, signal?: AbortSignal) => request(`/incidents/${encodeURIComponent(id)}/${agent ? 'agent-investigations' : 'investigations'}?limit=20`, historySchema, signal),
  investigation: (id: string, signal?: AbortSignal) => request(`/investigations/${encodeURIComponent(id)}`, investigationSchema, signal),
  createIncident: (title: string, asOf: string) => request('/incidents', incidentSchema, undefined, false, { title, description: 'User-defined hypothetical disruption from the Houston spatial workspace. No real road closure is asserted.', kind: 'hypothetical', occurred_at: asOf, context: { latitude: 29.7075, longitude: -95.395 }, claims: [{ kind: 'hypothetical', statement: 'Assume the explicitly selected OSM endpoint pairs are closed for this comparison only.', source: 'LifelineTwin spatial workspace', observed_at: asOf }] }),
  investigate: (id: string, asOf: string, closures: Scenario['analysis']['closures']) => request(`/incidents/${encodeURIComponent(id)}/investigations`, investigationSchema, undefined, false, { as_of: asOf, mode: 'cache', variable: 'temperature_2m', selection: 'provided', closures: closures.map(({ id, u, v }) => ({ id, u, v })) }),
}
