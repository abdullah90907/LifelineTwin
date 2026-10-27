"""Real HTTP demonstration with a real server restart; no geographic/model downloads.

Run from anywhere using the existing migration environment. A fresh evidence
directory and SQLite database are allocated for every run, preserving old results.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx

from lifelinetwin_backend.config import Settings
from lifelinetwin_geo.data import load
from lifelinetwin_geo.engine import analyze
from lifelinetwin_geo.analysis_25 import choose_closures_by_betweenness


def main():
    evidence = ROOT / "evidence/phase4a"
    evidence.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="heidelberg-demo-", dir=evidence))
    config = Settings()
    graph, origins, facilities, manifest = load(config.geographic_cache)
    phase2 = analyze(graph, origins, facilities)
    closures = choose_closures_by_betweenness(graph, phase2["baseline"], count=3,
        exclude_pairs=[(c["u"], c["v"]) for c in phase2["closures"]])
    weather = json.loads(config.weather_snapshot.read_text(encoding="utf-8"))
    as_of = weather["retrieved_utc"]
    incident = {"title": "Hypothetical Heidelberg corridor investigation", "kind": "hypothetical",
        "description": "Reproducible research stress test; no real-world disruption is asserted.",
        "occurred_at": as_of, "context": {"latitude": 49.415, "longitude": 8.6775},
        "claims": [{"kind": "hypothetical", "source": "Computed baseline-used edge betweenness; Phase 2 pairs excluded",
                    "statement": "Assume these graph segments are closed simultaneously for comparison only.", "observed_at": as_of}]}
    investigation_request = {"as_of": as_of, "mode": "cache", "variable": "temperature_2m",
                            "closures": [{k: c[k] for k in ("id", "u", "v")} for c in closures]}
    (output / "requests.json").write_text(json.dumps({"incident": incident, "investigation": investigation_request}, indent=2), encoding="utf-8")
    env = os.environ.copy()
    env.update(LIFELINETWIN_DATABASE=str(output / "demo.sqlite3"), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    transcript = []
    client = httpx.Client(base_url=url, timeout=180, trust_env=False)

    def call(method, path, payload=None):
        response = client.request(method, path, json=payload) if payload is not None else client.request(method, path)
        transcript.append({"method": method, "path": path, "status": response.status_code, "body": response.json()})
        response.raise_for_status()
        return response.json()

    def start(log):
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "lifelinetwin_backend.main:app",
            "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env,
            stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError("Server exited; inspect the saved server log")
                try:
                    if client.get("/health").status_code == 200:
                        return process
                except httpx.TransportError:
                    pass
                time.sleep(0.5)
            raise RuntimeError("Server startup timed out")
        except BaseException:
            process.terminate()
            process.wait(timeout=20)
            raise

    def stop(process):
        process.terminate()
        process.wait(timeout=20)

    try:
        with (output / "server-first.log").open("w", encoding="utf-8") as log:
            process = start(log)
            try:
                call("GET", "/health")
                created = call("POST", "/incidents", incident)
                iid = created["id"]
                call("PATCH", f"/incidents/{iid}/status", {"status": "investigating"})
                saved = call("POST", f"/incidents/{iid}/investigations", investigation_request)
                assert saved["status"] == "completed"
            finally:
                stop(process)
        with (output / "server-restarted.log").open("w", encoding="utf-8") as log:
            process = start(log)
            try:
                restored = call("GET", f"/investigations/{saved['id']}")
                assert restored == saved, "Persisted investigation differs after process restart"
                assert call("GET", f"/incidents/{iid}")["status"] == "investigating"
                assert len(call("GET", f"/incidents/{iid}/investigations")) == 1
                assert len(call("GET", f"/incidents/{iid}/observations")) == 1
                call("GET", f"/investigations/{saved['id']}/recommendations")
            finally:
                stop(process)
        result = saved["result"]
        summary = {"hypothetical": True, "incident_id": iid, "investigation_id": saved["id"],
                   "server_process_restarted": True, "persisted_result_identical": restored == saved,
                   "graph_nodes": manifest["nodes"], "graph_edges": manifest["directed_edges"],
                   "pair_restorations": [{k: r[k] for k in ("reopened", "reconnected_origins", "distance_saved_m_for_already_reachable")}
                                         for r in result["geography"]["pair_restorations"]],
                   "model": result["environment"]["forecast"]["model_id"],
                   "observed_context_hours": result["environment"]["observations"]["n_hours"],
                   "forecast_horizon_hours": result["environment"]["forecast"]["forecast_horizon_hours"]}
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps({"evidence_directory": str(output), **summary}, indent=2))
    finally:
        (output / "http-transcript.json").write_text(json.dumps(transcript, indent=2), encoding="utf-8")
        client.close()


if __name__ == "__main__":
    main()
