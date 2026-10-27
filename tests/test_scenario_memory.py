"""Real sponsor reference engine plus bounded, sanitized failure paths (offline)."""
import subprocess
import unittest
from unittest.mock import patch

from lifelinetwin_backend.config import Settings
from lifelinetwin_backend.schemas import GeographicRequest
from lifelinetwin_backend.services import Tools
from lifelinetwin_backend.scenario_memory import project_scenario


class ScenarioMemoryTests(unittest.TestCase):
    def test_real_meterless_tracks_computed_restoration_without_changing_osm(self):
        geo = Tools(Settings()).geographic(GeographicRequest(selection="betweenness", count=3))
        choices = geo.pair_restorations or geo.analysis["restorations"]
        best = max(choices, key=lambda r: (r["reconnected_origins"], r["distance_saved_m_for_already_reachable"]))
        output = project_scenario("offline-real-tools", geo.analysis["closures"], best)
        self.assertEqual(output["status"], "verified", output)
        self.assertTrue(output["hypothetical"])
        for road, segment in zip(output["roads"], geo.analysis["closures"]):
            self.assertEqual((road["u"], road["v"]), (segment["u"], segment["v"]))
            self.assertEqual(road["duplicate_replay_appended_events"], 0)
            self.assertEqual(road["active_source"]["kind"], "hypothetical-scenario")
            if segment["id"] in best["reopened"]:
                self.assertEqual(road["projected_status"], "restoration_preview_open")
                self.assertEqual(road["facts"][0]["supersededBy"], road["facts"][1]["id"])
            else:
                self.assertEqual(road["projected_status"], "assumed_closed")
        self.assertEqual(Tools(Settings()).geographic(GeographicRequest(selection="betweenness", count=3)), geo)

    def test_missing_runtime_is_explicit_and_does_not_start_process(self):
        with patch("lifelinetwin_backend.scenario_memory.shutil.which", return_value=None), \
             patch.dict("os.environ", {}, clear=True), patch("subprocess.run") as run:
            self.assertEqual(project_scenario("test", [], None)["status"], "unavailable")
            run.assert_not_called()

    def test_timeout_and_stderr_are_sanitized_and_not_retried(self):
        for error in (subprocess.TimeoutExpired("node", 15, stderr="sensitive body"),
                      subprocess.CalledProcessError(1, "node", stderr="sensitive body")):
            with patch("subprocess.run", side_effect=error) as run:
                result = project_scenario("test", [], None)
                self.assertEqual(result["status"], "unavailable")
                self.assertNotIn("sensitive", str(result))
                run.assert_called_once()

    def test_no_benefit_does_not_project_a_reopening(self):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, '{"status":"verified","roads":[]}')) as run:
            project_scenario("test", [], {"reopened": "D1", "reconnected_origins": 0, "distance_saved_m_for_already_reachable": 0})
            self.assertIn('"reopened": []', run.call_args.kwargs["input"])
