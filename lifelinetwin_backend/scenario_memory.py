"""Optional real Meterless projection. SQLite retains the accepted output.

No geographic calculations or real road-status assertions occur here. A fresh
in-memory engine avoids relying on the reference engine's known reopen issue.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def project_scenario(incident_id, closures, best):
    node = os.environ.get("LIFELINETWIN_NODE") or shutil.which("node")
    runner = ROOT / "vendor/Meterless/engines/world-model/reference/node_modules/tsx/dist/cli.mjs"
    unavailable = {"status": "unavailable", "engine": "Meterless WorldModel reference",
                   "reason": "Local Meterless runtime unavailable; analytical results remain valid."}
    if not node or not runner.is_file():
        return unavailable
    reopened = best["reopened"] if best else []
    if isinstance(reopened, str):
        reopened = [reopened]
    # Restoration projection only when the computed alternative has a benefit.
    if best and not (best["reconnected_origins"] or best["distance_saved_m_for_already_reachable"] > 1e-8):
        reopened = []
    payload = {"incident_id": incident_id, "closures": closures, "reopened": reopened}
    try:
        completed = subprocess.run([node, str(runner), str(ROOT / "scripts/scenario-memory.ts")],
            input=json.dumps(payload), capture_output=True, text=True, timeout=15,
            cwd=ROOT, check=True)
        if len(completed.stdout) > 200_000:
            return unavailable | {"reason": "Meterless projection exceeded the bounded output limit."}
        output = json.loads(completed.stdout)
        if output.get("status") != "verified" or len(output.get("roads", [])) != len(closures):
            return unavailable
        return output
    except (OSError, subprocess.SubprocessError, ValueError):
        # Never store raw stderr, environment variables, or provider bodies.
        return unavailable
