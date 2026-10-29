import { z } from 'zod'
import { request } from './api'
const community=z.object({id:z.string(),name:z.string(),source:z.string().optional()})
const facility=z.object({id:z.string(),name:z.string(),source:z.string().optional(),capability_status:z.string().optional(),service_source:z.string().optional(),service_reviewed_on:z.string().optional()})
export const regionsSchema=z.array(z.object({id:z.enum(['houston','alabama']),name:z.string(),focus:z.string(),ready:z.boolean(),communities:z.array(community),facilities:z.array(facility),snapshot_at:z.string().nullable()}))
const feed=z.object({status:z.enum(['available','unavailable']),source_url:z.string(),retrieved_at:z.string()})
const alert=z.object({id:z.string(),event:z.string().nullable(),severity:z.string().nullable(),headline:z.string().nullable(),description:z.string().nullable(),instruction:z.string().nullable(),expires:z.string().nullable()})
export const signalsSchema=z.object({region:z.string(),coverage:z.string(),alerts:feed.extend({data:z.array(alert).nullable()}),weather:feed.extend({data:z.object({current:z.object({time:z.string(),temperature_2m:z.number().nullable(),precipitation:z.number().nullable(),wind_speed_10m:z.number().nullable()})}).passthrough().nullable()})})
const result=z.object({region:z.string(),region_name:z.string(),computed_at:z.string(),verification:z.string(),input_sha256:z.string(),
 summary:z.object({communities_evaluated:z.number(),communities_with_longer_routes:z.number(),communities_newly_disconnected:z.number(),largest_increase_m:z.number(),population_affected:z.number().nullable()}),
 communities:z.array(z.object({id:z.string(),name:z.string(),source:z.string().nullable().optional(),baseline_m:z.number().nullable(),scenario_m:z.number().nullable(),increase_m:z.number().nullable(),newly_disconnected:z.boolean(),alternative_facility:z.string().nullable()})),
 alternatives:z.array(z.object({id:z.string(),action:z.string(),kind:z.string(),reconnected_communities:z.number(),communities_with_shorter_routes:z.number().optional(),mean_distance_saved_m:z.number().optional(),distance_saved_m:z.number(),assumption:z.string()})),limitations:z.array(z.string())})
export const caseSchema=z.object({id:z.string(),region:z.string(),created_at:z.string(),request:z.object({title:z.string(),source:z.string(),observed_at:z.string(),evidence_kind:z.string()}).passthrough(),result})
export type ContinuityCase=z.infer<typeof caseSchema>
export type RegionId='houston'|'alabama'
export const selectedRoadsSchema=z.array(z.object({id:z.string(),u:z.number().int(),v:z.number().int()})).max(6)
export const continuityApi={
 regions:(signal?:AbortSignal)=>request('/continuity/regions',regionsSchema,signal),
 signals:(region:RegionId,signal?:AbortSignal)=>request(`/continuity/signals/${region}`,signalsSchema,signal),
 cases:(region:RegionId,signal?:AbortSignal)=>request(`/continuity/cases?region=${region}`,z.array(caseSchema),signal),
 create:(body:unknown)=>request('/continuity/cases',caseSchema,undefined,false,body),
}
