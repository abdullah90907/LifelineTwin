"""Read-only verification of a saved UI-created investigation; never creates a run."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("id")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    # Fixed loopback only. UUID validation prevents URL/path injection.
    from uuid import UUID
    identifier = str(UUID(args.id))
    with urlopen(f"http://127.0.0.1:{args.port}/investigations/{identifier}", timeout=30) as response:
        record = json.load(response)
    if args.compare:
        assert record == json.loads(args.compare.read_text(encoding="utf-8")), "Restart changed saved output"
    result = record["result"]
    assert record["status"] == "completed"
    from lifelinetwin_geo.data import load
    from lifelinetwin_geo.engine import accessibility, close_segments
    from lifelinetwin_backend.config import Settings
    graph, origins, facilities, _ = load(Settings().geographic_cache)
    geo = result["geography"]["analysis"]
    assert geo["baseline"] == accessibility(graph, origins, facilities)
    assert geo["disrupted"] == accessibility(close_segments(graph, geo["closures"]), origins, facilities)
    for alternative in geo["restorations"] + result["geography"]["pair_restorations"]:
        reopened = alternative["reopened"]
        if isinstance(reopened, str):
            reopened = [reopened]
        direct = accessibility(close_segments(graph, [c for c in geo["closures"] if c["id"] not in reopened]), origins, facilities)
        assert direct == alternative["accessibility"]
        saved = sum(before["distance_m"] - after["distance_m"] for before, after in zip(geo["disrupted"], direct)
                    if before["distance_m"] is not None and after["distance_m"] is not None)
        assert abs(saved - alternative["distance_saved_m_for_already_reachable"]) < 1e-8
    evidence = {e["id"] for e in result["evidence"]}
    assert all(set(r["evidence_refs"]) <= evidence for r in result["recommendations"])
    assert result["scenario_memory"]["status"] == "verified"
    assert not result["environment"]["provenance"]["weather_implies_road_closure"]
    serialized = json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False)
    # Never overwrite previous evidence.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({"status": "PASS", "investigation_id": identifier,
        "sha256_canonical_record": hashlib.sha256(serialized.encode()).hexdigest(),
        "direct_geographic_comparison": True, "recommendation_references_resolved": True,
        "meterless_verified": True, "restart_identical": bool(args.compare)}))


if __name__ == "__main__":
    main()
