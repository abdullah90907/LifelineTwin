"""Heidelberg agent demo. --controlled-fake is a TEST, not live LLM evidence.

Without that flag this requires explicit provider configuration and invokes the
real SDK. Every run creates a new evidence directory/database and restarts its
own localhost server before retrieving stored results and traces.
"""
import argparse
import json
import multiprocessing as mp
import socket
import sys
import tempfile
import time
from pathlib import Path
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from lifelinetwin_backend.config import Settings
from lifelinetwin_backend.agent_provider import ProviderConfig, ProviderConfigurationError


def tool_call(name, arguments, cid):
    return {"id": cid, "name": name, "arguments": json.dumps(arguments)}


class ControlledDemoProvider:
    """CONTROLLED FAKE LLM solely for testing orchestration with real tools."""
    secret = ""
    identity = {"adapter": "controlled_fake_demo_test_only", "configured_model": "controlled-fake", "live_llm": False}

    def complete(self, messages, tools, timeout):
        n = sum(m["role"] == "assistant" for m in messages)
        request = json.loads(messages[1]["content"])
        ids = [c["id"] for c in request["allowed_hypothetical_closures"]]
        citation = {"evidence_id": "E4", "pointer": "/pair_restorations/0"}
        rounds = [
            [tool_call("baseline_accessibility", {}, "b"), tool_call("retrieve_observations", {}, "o")],
            [tool_call("generate_forecast", {}, "f"), tool_call("compare_restorations", {"closure_ids": ids}, "r")],
            [tool_call("inspect_evidence", citation, "i")],
            [tool_call("complete_investigation", {"findings": [citation,
                {"evidence_id": "E3", "pointer": "/forecast/forecast_horizon_hours"},
                {"evidence_id": "E2", "pointer": "/provenance/product_type"}],
                "uncertainties": ["historical_snapshot", "distance_only", "weather_not_causal"],
                "actions": [{"kind": "evaluate_restoration", "citations": [citation]},
                            {"kind": "verify_road_status", "citations": [{"evidence_id": "E0", "pointer": "/kind"}]}]}, "done")],
        ]
        return {"model": "controlled-fake-NOT-live-LLM", "note": "CONTROLLED TEST ONLY: predetermined tool selection", "calls": rounds[min(n, len(rounds)-1)]}


def server(database_path, port, fake):
    import uvicorn
    from lifelinetwin_backend.main import create_app
    app = create_app(replace(Settings(), database_path=Path(database_path)),
                     agent_provider_factory=ControlledDemoProvider if fake else None)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controlled-fake", action="store_true", help="Test only; never claimed as genuine LLM evidence")
    args = parser.parse_args()
    if not args.controlled_fake:
        try:
            ProviderConfig.from_environment()
        except ProviderConfigurationError as exc:
            print(json.dumps({"status": "not_configured", "live_llm_executed": False, "error": str(exc)}))
            return 2
    from lifelinetwin_geo.data import load
    from lifelinetwin_geo.engine import analyze, accessibility, close_segments
    from lifelinetwin_geo.analysis_25 import choose_closures_by_betweenness
    settings = Settings()
    graph, origins, facilities, _ = load(settings.geographic_cache)
    initial = analyze(graph, origins, facilities)
    closures = choose_closures_by_betweenness(graph, initial["baseline"], count=3,
        exclude_pairs=[(c["u"], c["v"]) for c in initial["closures"]])
    weather = json.loads(settings.weather_snapshot.read_text(encoding="utf-8"))
    as_of = weather["retrieved_utc"]
    incident = {"title": "Hypothetical Heidelberg Phase 4B research demonstration", "kind": "hypothetical",
        "description": "Research scenario only. These cached endpoints are not evidence of real closures.", "occurred_at": as_of}
    approved = [{k: c[k] for k in ("id", "u", "v")} for c in closures]
    question = "Investigate the approved hypothetical closures, compare hospital accessibility and restoration pairs by OSM endpoints, and inspect cached environmental observations and TTM forecasts. Give cited advisory findings and limitations."
    request = {"question": question, "as_of": as_of, "allowed_closures": approved, "mode": "cache", "max_iterations": 8,
               "max_tool_calls": 14, "timeout_seconds": 240, "tool_timeout_seconds": 60}
    parent = ROOT / "evidence/phase4b"
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="controlled-test-" if args.controlled_fake else "live-llm-", dir=parent))
    (output / "requests.json").write_text(json.dumps({"incident": incident, "agent_request": request}, indent=2), encoding="utf-8")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=300, trust_env=False)
    transcript = []
    context = mp.get_context("spawn")

    def start():
        process = context.Process(target=server, args=(str(output / "demo.sqlite3"), port, args.controlled_fake))
        process.start()
        try:
            for _ in range(120):
                if not process.is_alive():
                    raise RuntimeError("Demo server exited")
                try:
                    if client.get("/health").status_code == 200:
                        return process
                except httpx.TransportError:
                    pass
                time.sleep(0.5)
            raise RuntimeError("Demo server startup timed out")
        except BaseException:
            process.terminate()
            process.join(timeout=5)
            raise

    def stop(process):
        process.terminate()
        process.join(timeout=10)
        if process.is_alive():
            process.kill()
            process.join(timeout=5)

    def api(method, path, payload=None):
        response = client.request(method, path, json=payload) if payload is not None else client.request(method, path)
        response.raise_for_status()
        data = response.json()
        transcript.append({"method": method, "path": path, "status": response.status_code, "body": data})
        return data

    try:
        process = start()
        try:
            iid = api("POST", "/incidents", incident)["id"]
            deterministic = api("POST", f"/incidents/{iid}/investigations", {"as_of": as_of, "closures": approved, "mode": "cache"})
            run = api("POST", f"/incidents/{iid}/agent-investigations", request)
            trace = api("GET", f"/agent-investigations/{run['id']}/trace")
        finally:
            stop(process)
        process = start()
        try:
            restored = api("GET", f"/agent-investigations/{run['id']}")
            restored_trace = api("GET", f"/agent-investigations/{run['id']}/trace")
            assert restored == run and restored_trace == trace
        finally:
            stop(process)
        alternatives = deterministic["result"]["geography"]["pair_restorations"]
        by_id = {c["id"]: c for c in closures}
        verification = []
        for pair in alternatives:
            reopened = pair["reopened"]
            remaining = [c for c in closures if c["id"] not in reopened]
            routes = accessibility(close_segments(graph, remaining), origins, facilities)
            disrupted = deterministic["result"]["geography"]["analysis"]["disrupted"]
            saved = sum(max(0, a["distance_m"]-b["distance_m"]) for a,b in zip(disrupted,routes,strict=True)
                        if a["distance_m"] is not None and b["distance_m"] is not None)
            assert abs(saved-pair["distance_saved_m_for_already_reachable"]) < 1e-7
            verification.append({"osm_segments": [{"u": by_id[c]["u"], "v": by_id[c]["v"]} for c in reopened],
                "saved_origin_metres": saved, "direct_graph_verification": True})
        agent_geo = [e["payload"]["output"] for e in trace if e["kind"] == "tool" and e["payload"].get("category") == "computed_hypothetical_geography"
                     and e["payload"].get("tool") == "compare_restorations" and not e["payload"].get("error")]
        summary = {"controlled_fake_test": args.controlled_fake, "live_llm_executed": not args.controlled_fake,
            "run_status": run["status"], "incident_id": iid, "agent_run_id": run["id"],
            "server_process_restarted": True, "saved_run_and_trace_identical": restored == run and restored_trace == trace,
            "selected_tools": [e["payload"]["tool"] for e in trace if e["kind"] in ("tool", "final")],
            "restoration_endpoint_verification": verification,
            "agent_and_phase4a_pair_metrics_equal": bool(agent_geo) and
                [r["distance_saved_m_for_already_reachable"] for r in agent_geo[0]["pair_restorations"]] == [r["distance_saved_m_for_already_reachable"] for r in alternatives],
            "note": "Controlled fake selection is orchestration evidence only; no claim the agent is better than deterministic Phase 4A."}
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps({"evidence_directory": str(output), **summary}, indent=2))
        return 0 if run["status"] == "completed" else 1
    finally:
        (output / "http-transcript.json").write_text(json.dumps(transcript, indent=2), encoding="utf-8")
        client.close()


if __name__ == "__main__":
    sys.exit(main())
