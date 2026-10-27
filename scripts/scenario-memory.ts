// Real Meterless engine: scenario-assumption provenance, never observed road state.
import { readFileSync } from 'node:fs';
import { WorldModel } from '../vendor/Meterless/engines/world-model/reference/src/index.ts';

const input = JSON.parse(readFileSync(0, 'utf8'));
if (!Array.isArray(input.closures) || input.closures.length > 6) throw new Error('Invalid scenario');
const world = new WorldModel({ storage: 'memory', namespace: 'lifelinetwin-scenario', conflictPolicy: 'most-recent-wins' });
const roads = [];
for (const road of input.closures) {
  const source = (step: number) => ({ kind: 'hypothetical-scenario', by: 'LifelineTwin deterministic investigation',
    at: `2000-01-01T00:00:0${step}.000Z`, runId: `${input.incident_id}:${road.id}:${step}`,
    url: `urn:lifelinetwin:incident:${input.incident_id}:geography:${road.id}` });
  const entity = await world.upsertEntity({ type: 'road', externalKey: { system: 'osm-endpoint-pair', id: `${road.u}:${road.v}` },
    attrs: { hypothetical: true, u: road.u, v: road.v }, source: source(0) });
  await world.assertFact({ about: entity.id, predicate: 'scenario_status', value: 'assumed_closed', source: source(1) });
  if (input.reopened.includes(road.id)) await world.assertFact({ about: entity.id, predicate: 'scenario_status', value: 'restoration_preview_open', source: source(2) });
  const facts = world.view('facts').about(entity.id);
  const count = world.events().length;
  const latest = facts.filter(f => !f.supersededBy)[0];
  await world.assertFact({ about: entity.id, predicate: 'scenario_status', value: latest.value, source: latest.source });
  if (world.events().length !== count) throw new Error('Duplicate replay appended events');
  roads.push({ segment_id: road.id, u: road.u, v: road.v, projected_status: world.view('graph').entity(entity.id)?.attrs.scenario_status,
    facts, active_source: latest.source, duplicate_replay_appended_events: world.events().length - count });
}
console.log(JSON.stringify({ status: 'verified', engine: 'Meterless WorldModel reference', hypothetical: true,
  purpose: 'Resolve closure assumptions against the computed restoration preview with field-level provenance.',
  ordering: 'Logical scenario order; 2000 timestamps are sequence markers, not event observation times.',
  persistence: 'Accepted projection stored by LifelineTwin SQLite; no upstream disk-reopen claim.', roads }));
