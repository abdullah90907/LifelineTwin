import argparse
import json
import sys
from pathlib import Path
from .engine import analyze


def main():
    # Windows redirects otherwise use a legacy code page, corrupting OSM names.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Distance-based hospital accessibility; hypothetical closures only")
    parser.add_argument("command", choices=["download", "analyze"])
    parser.add_argument("--cache", default="data/heidelberg")
    parser.add_argument("--output", default="evidence/phase2-results.json")
    args = parser.parse_args()
    from .data import download, load, write_json
    try:
        if args.command == "download":
            print(download(args.cache))
            return 0
        graph, origins, facilities, manifest = load(args.cache)
        result = analyze(graph, origins, facilities)
        result.update(dataset=manifest, origins=origins, facilities=facilities)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        write_json(args.output, result)
        print(f"{manifest['area']} | {graph.number_of_nodes()} nodes / {graph.number_of_edges()} directed edges")
        print("OpenStreetMap contributors | DISTANCE ONLY, not travel time | HYPOTHETICAL closures")
        for f in facilities:
            print(f"Hospital: {f['name']} [{f['id']}] snap={f['snap_distance_m']:.0f} m")
        print("Origin    Baseline m   Closures m    Increase m")
        fmt = lambda value: "unreachable" if value is None else f"{value:.1f}"
        for row in result["changes"]:
            delta = "n/a" if row['increase_m'] is None else fmt(row['increase_m'])
            print(f"{row['id']:8} {fmt(row['baseline_m']):>11} {fmt(row['scenario_m']):>12} {delta:>13}")
        print("Origin snap offsets (metres, excluded from routing): " + ", ".join(f"{o['id']}={o['snap_distance_m']:.0f}" for o in origins))
        print("Newly disconnected:", sum(r['newly_disconnected'] for r in result['changes']))
        for c in result['closures']:
            print(f"{c['id']}: {c['name']} endpoints {c['u']} <-> {c['v']}")
        print("Restorations ranked by reconnected origins, then metres saved for already-reachable origins:")
        for i, r in enumerate(result['restorations'], 1):
            print(f"{i}. Reopen {r['reopened']}: reconnect {r['reconnected_origins']}; save {r['distance_saved_m_for_already_reachable']:.1f} origin-metres")
        print(f"Detailed routes, provenance, and scenario distances: {args.output}")
        return 0
    except Exception as error:
        print(f"{args.command} FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        print("No real-data completion claimed. Synthetic unit tests validate only the algorithm.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
