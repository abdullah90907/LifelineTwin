import sys, json
from pathlib import Path
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from lifelinetwin_geo.data import load
from lifelinetwin_geo.analysis_25 import analyze_25

PHASE2_PAIRS = [(11247599,11247600),(11247645,645759168),(13888159,301109705)]
graph, origins, facilities, manifest = load("data/heidelberg")
result = analyze_25(graph, origins, facilities, exclude_pairs=PHASE2_PAIRS, count=3)
result.update(dataset=manifest, origins=origins, facilities=facilities)

lines = []
lines.append(manifest["area"] + " | " + str(graph.number_of_nodes()) + " nodes / " + str(graph.number_of_edges()) + " directed edges")
lines.append("OpenStreetMap contributors | DISTANCE ONLY, not travel time | HYPOTHETICAL closures")
lines.append("Closure selection: " + result["selection_method"])
lines.append("")
for c in result["closures"]:
    lines.append(c["id"] + ": " + c["name"] + " endpoints " + str(c["u"]) + " <-> " + str(c["v"]) + "  betweenness=" + f"{c['betweenness_score']:.6f}")
lines.append("")

def fmt(v):
    return "unreachable" if v is None else f"{v:.1f}"

lines.append(f"{'Origin':8} {'Baseline m':>11} {'Disrupted m':>12} {'Increase m':>12}")
for row in result["changes"]:
    delta = "n/a" if row["increase_m"] is None else fmt(row["increase_m"])
    dc = "  DISCONNECTED" if row["newly_disconnected"] else ""
    lines.append(f"{row['id']:8} {fmt(row['baseline_m']):>11} {fmt(row['scenario_m']):>12} {delta:>12}{dc}")

nd = sum(r["newly_disconnected"] for r in result["changes"])
total = sum(r["increase_m"] for r in result["changes"] if r["increase_m"] is not None)
baseline_mean = sum(r["distance_m"] for r in result["baseline"] if r["distance_m"] is not None) / len(result["baseline"])
disrupted_mean = sum(r["distance_m"] for r in result["disrupted"] if r["distance_m"] is not None) / len(result["disrupted"])

lines.append("")
lines.append("Newly disconnected: " + str(nd))
lines.append(f"Total route-distance increase: {total:.1f} m")
lines.append(f"Mean baseline dist: {baseline_mean:.1f} m")
lines.append(f"Mean disrupted dist: {disrupted_mean:.1f} m  (+{disrupted_mean-baseline_mean:.1f} m, +{100*(disrupted_mean-baseline_mean)/baseline_mean:.1f}%)")
lines.append("")
lines.append("Restorations ranked by reconnected origins then metres saved:")
for i, r in enumerate(result["restorations"], 1):
    lines.append(str(i) + ". Reopen " + r["reopened"] + ": reconnect " + str(r["reconnected_origins"]) + " origins; save " + f"{r['distance_saved_m_for_already_reachable']:.1f}" + " origin-metres")
    for row in r["accessibility"]:
        old = next(x for x in result["disrupted"] if x["id"] == row["id"])
        if old["distance_m"] != row["distance_m"] and old["distance_m"] is not None and row["distance_m"] is not None:
            delta = row["distance_m"] - old["distance_m"]
            lines.append("   " + row["id"] + ": disrupted=" + fmt(old["distance_m"]) + " -> restored=" + fmt(row["distance_m"]) + " (delta=" + f"{delta:.1f}" + " m)")
lines.append("")
lines.append("Origin snap offsets (metres, excluded from routing): " + ", ".join(o["id"] + "=" + f"{o['snap_distance_m']:.0f}" for o in origins))
lines.append("")

output = "\n".join(lines)
print(output)
Path("evidence/phase2-5-cli.txt").write_text(output, encoding="utf-8")

# Also save full JSON
Path("evidence/phase2-5-results.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
print("Written evidence/phase2-5-cli.txt and evidence/phase2-5-results.json")
