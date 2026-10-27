// Real upstream reference engine; only the road observations are synthetic.
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import path from "node:path";
import { WorldModel } from "../vendor/Meterless/engines/world-model/reference/src/index.ts";

const directory = mkdtempSync(path.resolve("evidence/road-run-"));
const options = { storage: "local" as const, namespace: "lifelinetwin-phase1", directory,
  conflictPolicy: "most-recent-wins" as const };
const world = new WorldModel(options);
const source = (at: string, runId: string) => ({ kind: "synthetic-test", by: "lifelinetwin-phase1",
  at, runId, url: `urn:lifelinetwin:synthetic:${runId}` });
const first = source("2026-10-24T08:00:00.000Z", "road-closure-001");
const later = source("2026-10-24T09:00:00.000Z", "road-update-002");
const road = await world.upsertEntity({ type: "road", externalKey: { system: "synthetic", id: "R001" },
  name: "Synthetic Hospital Access Road", attrs: { synthetic: true }, source: first });
await world.assertFact({ about: road.id, predicate: "status", value: "closed", confidence: 1, source: first });
assert.equal(world.view("graph").entity(road.id)?.attrs.status, "closed");
await world.assertFact({ about: road.id, predicate: "status", value: "restricted", confidence: 1, source: later });
const latest = world.view("graph").entity(road.id);
const facts = world.view("facts").about(road.id);
const active = facts.filter(f => !f.supersededBy);
assert.equal(latest?.attrs.status, "restricted");
assert.equal(facts.length, 2);
assert.equal(active.length, 1);
assert.deepEqual(active[0].source, later);
assert.equal(facts[0].supersededBy, active[0].id);
const beforeReplay = world.events().length;
await world.assertFact({ about: road.id, predicate: "status", value: "restricted", confidence: 1, source: later });
assert.equal(world.events().length, beforeReplay);
console.log(JSON.stringify({ result: "PASS", entityId: road.id,
  initialStatus: "closed", latestStatus: latest?.attrs.status,
  latestStatusProvenance: active[0].source, facts,
  replayAppendedEvents: world.events().length - beforeReplay,
  scope: "in-process writes, reads, provenance, and duplicate replay", audit: world.audit(),
  persistedFile: path.join(directory, ".world", `${options.namespace}.json`) }, null, 2));
if (process.argv.includes("--check-reopen")) {
  const reopened = new WorldModel(options);
  assert.equal(reopened.view("graph").entity(road.id)?.attrs.status, "restricted",
    "Reference persistence must restore the projected status after reopening");
  assert.deepEqual(reopened.view("facts").about(road.id), facts);
  assert.equal(reopened.audit().length, 3);
  console.log("Persistence reopen: PASS");
}
