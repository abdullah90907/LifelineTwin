"""Bounded genuine hosted-LLM verification. Never accepts credentials on argv/files.

Use configured provider environment variables. --stdin-key supports an ephemeral
credential on a non-echoed pipe; it is set only in this process's environment.
One small API probe and one bounded agent investigation are attempted. No fake
provider exists in this script. All saved JSON is redacted before writing.
"""
import argparse
import hashlib
import json
import logging
import multiprocessing as mp
import os
from pathlib import Path
import re
import socket
import sqlite3
import sys
import tempfile
import time
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
logging.disable(logging.CRITICAL)


def server(database, port):
    import uvicorn
    from lifelinetwin_backend.main import create_app
    from lifelinetwin_backend.config import Settings
    app = create_app(replace(Settings(), database_path=Path(database)))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="critical", access_log=False)


def redact(value, secret):
    if isinstance(value, str):
        value = value.replace(secret, "[REDACTED]") if secret else value
        return re.sub(r"gsk_[A-Za-z0-9_-]+", "[REDACTED]", value)
    if isinstance(value, dict):
        return {str(k): redact(v, secret) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secret) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdin-key", action="store_true")
    parser.add_argument("--final", action="store_true", help="One final bounded investigation; skip API probe and save separate final evidence")
    parser.add_argument("--diagnose-checkpoint", type=Path, help="One SDK-only diagnostic call from a failed saved checkpoint; no new investigation")
    args = parser.parse_args()
    if args.stdin_key:
        if sys.stdin.isatty():
            import getpass
            print("AWAITING_HIDDEN_EPHEMERAL_CREDENTIAL", flush=True)
            os.environ["LIFELINETWIN_LLM_API_KEY"] = getpass.getpass("Credential (input hidden): ").strip()
        else:
            print("AWAITING_EPHEMERAL_CREDENTIAL", flush=True)
            os.environ["LIFELINETWIN_LLM_API_KEY"] = sys.stdin.readline().strip()
    from lifelinetwin_backend.agent_provider import ProviderConfig
    config = ProviderConfig.from_environment()
    secret = config.api_key.get_secret_value()
    import httpx
    from openai import OpenAI

    parent = ROOT / ("evidence/phase4c-final" if args.final else "evidence/phase4c")
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="live-", dir=parent))
    summary = {"provider": "Groq", "base_url": config.base_url, "configured_model": config.model,
               "token_parameter": config.token_parameter, "fake_provider_used": False,
               "minimal_probe_attempted": False, "agent_endpoint_attempted": False,
               "live_agent_completed": False, "evidence_directory": str(output)}
    transcript = []

    def save(name, data):
        (output / name).write_text(json.dumps(redact(data, secret), indent=2, allow_nan=False), encoding="utf-8")

    def safe_error(exc):
        from lifelinetwin_backend.agent_failures import classify_exception
        return redact({"type": type(exc).__name__, **classify_exception(exc).model_dump()}, secret)

    try:
        if args.diagnose_checkpoint:
            from lifelinetwin_backend.agent_tools import tool_definitions
            with sqlite3.connect(args.diagnose_checkpoint) as db:
                checkpoint = json.loads(db.execute("SELECT checkpoint FROM agent_runs ORDER BY created_at DESC LIMIT 1").fetchone()[0])
            summary["checkpoint_diagnostic_attempted"] = True
            summary["diagnostic_input_characters"] = len(json.dumps(checkpoint["messages"]))
            with OpenAI(api_key=secret, base_url=config.base_url, timeout=25, max_retries=0) as sdk:
                diagnostic = sdk.chat.completions.create(model=config.model, messages=checkpoint["messages"],
                    tools=tool_definitions(), tool_choice="auto", **{config.token_parameter: 1800})
            summary["diagnostic"] = {"actual_model": diagnostic.model, "finish_reason": diagnostic.choices[0].finish_reason,
                "selected_tools": [c.function.name for c in (diagnostic.choices[0].message.tool_calls or [])],
                "usage": diagnostic.usage.model_dump() if diagnostic.usage else None}
            return 0
        if not args.final:
            summary["minimal_probe_attempted"] = True
            with OpenAI(api_key=secret, base_url=config.base_url, timeout=25, max_retries=0) as sdk:
                response = sdk.chat.completions.create(model=config.model,
                    messages=[{"role": "user", "content": "Reply exactly OK."}],
                    **{config.token_parameter: 128})
            probe = {"actual_model": response.model, "request_id": getattr(response, "_request_id", None),
                     "finish_reason": response.choices[0].finish_reason,
                     "tool_calls": [{"name": c.function.name, "arguments": c.function.arguments} for c in (response.choices[0].message.tool_calls or [])],
                     "usage": response.usage.model_dump() if response.usage else None}
            probe["completion_received"] = True
            probe["tool_calling_tested_in_probe"] = False
            save("minimal-probe.json", probe)
            summary["minimal_probe"] = probe

        from lifelinetwin_backend.config import Settings
        from lifelinetwin_backend.agent_tools import pointer_value
        from lifelinetwin_geo.data import load
        from lifelinetwin_geo.engine import analyze, close_segments, accessibility
        from lifelinetwin_geo.analysis_25 import choose_closures_by_betweenness
        settings = Settings()
        graph, origins, facilities, manifest = load(settings.geographic_cache)
        initial = analyze(graph, origins, facilities)
        closures = choose_closures_by_betweenness(graph, initial["baseline"], count=3,
            exclude_pairs=[(c["u"], c["v"]) for c in initial["closures"]])
        approved = [{k: c[k] for k in ("id", "u", "v")} for c in closures]
        source = json.loads(settings.weather_snapshot.read_text(encoding="utf-8"))
        as_of = source["retrieved_utc"]
        incident = {"title": "Hypothetical Heidelberg live LLM verification (Phase 4C final)" if args.final else "Hypothetical Heidelberg live LLM verification (Phase 4C)", "kind": "hypothetical",
            "description": "Research scenario only; approved cached road segments are hypothetical closures, not real incident reports.", "occurred_at": as_of}
        request = {"question": "Investigate all the approved hypothetical closure segments. Obtain baseline accessibility, before/after closure impacts and restoration comparisons including pairs, environmental observations, and the actual cached IBM TTM forecast. In the final structured findings cite exact distance impacts, the best reopening alternative with OSM endpoints, and at least one actual forecast value with its timestamp/unit. Recommendations must be advisory and tied to real tool evidence. Disclose snapshot and observation-versus-prediction limitations.",
            "as_of": as_of, "mode": "cache", "variable": "temperature_2m", "allowed_closures": approved,
            "max_iterations": 10 if args.final else 8, "max_tool_calls": 18 if args.final else 16, "timeout_seconds": 240, "tool_timeout_seconds": 60}
        save("requests.json", {"incident": incident, "agent_request": request})
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=290, trust_env=False)
        context = mp.get_context("spawn")

        def start():
            process = context.Process(target=server, args=(str(output / "verification.sqlite3"), port))
            process.start()
            try:
                for _ in range(120):
                    if not process.is_alive():
                        raise RuntimeError("Verification backend exited")
                    try:
                        if client.get("/health").status_code == 200:
                            return process
                    except httpx.TransportError:
                        pass
                    time.sleep(0.5)
                raise RuntimeError("Verification backend startup timed out")
            except BaseException:
                process.terminate()
                process.join(timeout=5)
                raise

        def stop(process):
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)

        def api(method, path, body=None):
            r = client.request(method, path, json=body) if body is not None else client.request(method, path)
            data = r.json()
            transcript.append({"method": method, "path": path, "status": r.status_code, "body": data})
            r.raise_for_status()
            return data

        try:
            process = start()
            try:
                iid = api("POST", "/incidents", incident)["id"]
                deterministic = api("POST", f"/incidents/{iid}/investigations", {"as_of": as_of, "mode": "cache", "closures": approved})
                summary["agent_endpoint_attempted"] = True
                run = api("POST", f"/incidents/{iid}/agent-investigations", request)
                trace = api("GET", f"/agent-investigations/{run['id']}/trace", None)
                save("agent-result-redacted.json", run)
                save("agent-trace-redacted.json", trace)
            finally:
                stop(process)
            process = start()
            try:
                after = api("GET", f"/agent-investigations/{run['id']}")
                after_trace = api("GET", f"/agent-investigations/{run['id']}/trace")
                summary["backend_restarted"] = True
                summary["saved_run_identical_after_restart"] = after == run
                summary["saved_trace_identical_after_restart"] = after_trace == trace
            finally:
                stop(process)
        finally:
            client.close()

        tool_events = [e["payload"] for e in trace if e["kind"] in ("tool", "final")]
        successful = [e for e in tool_events if e.get("error") is None]
        original_outputs = [e for e in successful if e.get("output") is not None]
        evidence = {"E0": {"data": json.loads(json.dumps(incident)), "category": "attributed_incident_claims"}}
        for e in original_outputs:
            if e.get("evidence_id"):
                evidence[e["evidence_id"]] = {"data": e["output"], "category": e["category"]}
        with sqlite3.connect(output / "verification.sqlite3") as db:
            checkpoint = json.loads(db.execute("SELECT checkpoint FROM agent_runs WHERE id=?", (run["id"],)).fetchone()[0])
            evidence = checkpoint["evidence"]
            summary["sqlite_integrity"] = db.execute("PRAGMA integrity_check").fetchone()[0]
        citation_checks = []
        recommendation_checks = []
        if run["result"]:
            for finding in run["result"]["findings"]:
                c = finding["citation"]
                citation_checks.append({"citation": c, "value_equals_tool_evidence":
                    finding["value"] == pointer_value(evidence[c["evidence_id"]]["data"], c["pointer"])})
            for action in run["result"]["recommendations"]:
                citations = []
                for c in action["citations"]:
                    value = pointer_value(evidence[c["evidence_id"]]["data"], c["pointer"])
                    citations.append({"citation": c, "resolves": True,
                        "osm_segments": value.get("osm_segments") if isinstance(value, dict) else None})
                recommendation_checks.append({"human_review_required": action["human_review_required"], "citations": citations})
        comparisons = []
        direct = deterministic["result"]["geography"]
        for e in original_outputs:
            if e.get("category") == "computed_hypothetical_geography":
                current = e["output"]
                original_pairs = {tuple(sorted((c["u"], c["v"]))) for c in current["analysis"]["closures"]}
                target_pairs = {tuple(sorted((c["u"], c["v"]))) for c in approved}
                if original_pairs == target_pairs:
                    comparisons.append({"tool": e["tool"], "closure_endpoints_equal": True,
                        "baseline_equal": current["analysis"]["baseline"] == direct["analysis"]["baseline"],
                        "changes_equal": current["analysis"]["changes"] == direct["analysis"]["changes"],
                        "pairs_equal": [{k: r[k] for k in ("reopened", "reconnected_origins", "distance_saved_m_for_already_reachable")}
                                        for r in current["pair_restorations"]] ==
                                       [{k: r[k] for k in ("reopened", "reconnected_origins", "distance_saved_m_for_already_reachable")}
                                        for r in direct["pair_restorations"]]})
        endpoint_checks = []
        by_id = {c["id"]: c for c in approved}
        for alternative in direct["pair_restorations"]:
            reopened = alternative["reopened"]
            restored = accessibility(close_segments(graph, [c for c in approved if c["id"] not in reopened]), origins, facilities)
            saved = sum(max(0, a["distance_m"]-b["distance_m"]) for a,b in zip(direct["analysis"]["disrupted"], restored, strict=True)
                        if a["distance_m"] is not None and b["distance_m"] is not None)
            endpoint_checks.append({"osm_segments": [{"u": by_id[c]["u"], "v": by_id[c]["v"]} for c in reopened],
                "saved_origin_metres": saved, "matches_deterministic": abs(saved-alternative["distance_saved_m_for_already_reachable"]) < 1e-8})
        forecasts = [e["output"]["forecast"] for e in original_outputs if e["tool"] == "generate_forecast"]
        forecast_equal = bool(forecasts) and forecasts[0]["forecast_values"] == deterministic["result"]["environment"]["forecast"]["forecast_values"]
        summary.update(incident_id=iid, agent_run_id=run["id"], status=run["status"],
            live_agent_completed=run["status"] == "completed", iterations=run["iterations"], tool_calls=run["tool_calls"],
            actual_models=[e["payload"]["model"] for e in trace if e["kind"] == "decision"],
            ordered_tool_calls=[{"tool": e["tool"], "error": e.get("error"), "evidence_id": e.get("evidence_id")} for e in tool_events],
            citation_checks=citation_checks, recommendation_citation_checks=recommendation_checks,
            sanitized_provider_failures=[e["payload"] for e in trace if e["kind"] == "provider_failure"],
            provider_attempts=checkpoint.get("provider_attempts"), retry_used=checkpoint.get("retry_used"),
            context_metrics=checkpoint.get("context_metrics",[]), usage_records=checkpoint.get("usage_records",[]),
            geographic_comparisons=comparisons, endpoint_verification=endpoint_checks,
            forecast_values_equal_phase4a=forecast_equal,
            successful_tools=sorted({e["tool"] for e in successful}),
            result_error=run["error"])
        # Scenario analysis already contains a baseline. Do not force a redundant
        # standalone baseline tool call merely to satisfy the verifier.
        required = {"retrieve_observations", "generate_forecast", "complete_investigation"}
        summary["all_requested_evidence_obtained"] = required <= set(summary["successful_tools"]) and bool(comparisons)
        save("deterministic-result.json", deterministic)
        save("http-transcript-redacted.json", transcript)
        return 0 if summary["live_agent_completed"] and summary["all_requested_evidence_obtained"] else 1
    except Exception as exc:
        summary["verification_error"] = safe_error(exc)
        return 1
    finally:
        save("http-transcript-redacted.json", transcript)
        summary["credential_present_in_saved_files"] = any(secret.encode() in p.read_bytes() for p in output.rglob("*") if p.is_file())
        save("summary.json", summary)
        print(json.dumps(redact(summary, secret), indent=2), flush=True)
        os.environ.pop("LIFELINETWIN_LLM_API_KEY", None)


if __name__ == "__main__":
    sys.exit(main())
