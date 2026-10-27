import argparse, json, sys
from pathlib import Path
from .engine import analyze

def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Phase 2.5: betweenness-driven scenario; hypothetical closures only")
    parser.add_argument("command", choices=["analyze25"])
    parser.add_argument("--cache", default="data/heidelberg")
    parser.add_argument("--output", default="evidence/phase2-5-results.json")
    parser.add_argument("--exclude-phase2", action="store_true", default=True,
                        help="Exclude Phase 2 closure pairs from selection (default: on)")
    args = parser.parse_args()
    from .data import load, write_json
    from .analysis_25 import analyze_25
    PHASE2_PAIRS = [
        (11247599, 11247600),
        (11247645, 645759168),
        (13888159, 301109705),
    ]
    try:
        graph, origins, facilities, manifest = load(args.cache)
        exclude = PHASE2_PAIRS if args.exclude_phase2 else None
        result = analyze_25(graph, origins, facilities, exclude_pairs=exclude, count=3)
        result.update(dataset=manifest, origins=origins, facilities=facilities)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        write_json(args.output, result)
        print(f"{manifest['"'"'area'"'"']} | {graph.number_of_nodes()} nodes / {graph.number_of_edges()} directed edges")
        print("OpenStreetMap contributors | DISTANCE ONLY, not travel time | HYPOTHETICAL closures")
        print(f"Closure selection: {result['"'"'selection_method'"'"']}")
        for c in result["closures"]:
            print(f"{c['"'"'id'"'"']}: {c['"'"'name'"'"']} endpoints {c['"'"'u'"'"']} <-> {c['"'"'v'"'"']}  betweenness={c['"'"'betweenness_score'"'"']:.6f}")
        fmt = lambda v: "unreachable" if v is None else f"{v:.1f}"
        print("Origin    Baseline m   Disrupted m    Increase m")
        for row in result["changes"]:
            delta = "n/a" if row['"'"'increase_m'"'"'] is None else fmt(row['"'"'increase_m'"'"'])
            print(f"{row['"'"'id'"'"']:8} {fmt(row['"'"'baseline_m'"'"']):>11} {fmt(row['"'"'scenario_m'"'"']):>12} {delta:>13}")
        nd = sum(r['"'"'newly_disconnected'"'"'] for r in result["changes"])
        print(f"Newly disconnected: {nd}")
        print("Restorations ranked by reconnected origins, then metres saved:")
        for i, r in enumerate(result["restorations"], 1):
            print(f"{i}. Reopen {r['"'"'reopened'"'"']}: reconnect {r['"'"'reconnected_origins'"'"']}; save {r['"'"'distance_saved_m_for_already_reachable'"'"']:.1f} origin-metres")
        print(f"Detailed results: {args.output}")
        return 0
    except Exception as error:
        print(f"{args.command} FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
