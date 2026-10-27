"""API, atomic persistence, real tool integration, and research provenance checks."""
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import networkx as nx
from fastapi.testclient import TestClient
from sqlalchemy import select, func

from lifelinetwin_backend.config import Settings, ROOT
from lifelinetwin_backend.database import InvestigationRow, ObservationRow, RecommendationRow
from lifelinetwin_backend.main import create_app
from lifelinetwin_backend.schemas import EnvironmentRequest, GeographicRequest, Incident, InvestigationRequest
from lifelinetwin_backend.services import Tools, ToolUnavailable


def incident_body():
    return {"title": "Hypothetical Heidelberg corridor disruption", "description": "Research scenario only; no real incident asserted.",
            "kind": "hypothetical", "occurred_at": "2026-10-24T19:55:49+00:00",
            "context": {"latitude": 49.415, "longitude": 8.6775},
            "claims": [{"kind": "hypothetical", "statement": "Assume selected segments are closed for comparison only",
                        "source": "Phase 4A research test", "observed_at": "2026-10-24T19:55:49+00:00"}]}


def investigation_body():
    return {"as_of": "2026-10-24T19:55:49+00:00", "mode": "cache", "closures": []}


class BackendApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = replace(Settings(), database_path=Path(self.temp.name) / "test.sqlite3")
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def create(self):
        response = self.client.post("/incidents", json=incident_body())
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    def test_incident_creation_status_and_history(self):
        iid = self.create()
        self.assertEqual(self.client.get("/health").json()["database"], "ok")
        self.assertEqual(len(self.client.get("/incidents").json()), 1)
        updated = self.client.patch(f"/incidents/{iid}/status", json={"status": "resolved"})
        self.assertEqual(updated.json()["status"], "resolved")
        self.assertEqual(self.client.get(f"/incidents/{iid}/investigations").json(), [])
        self.assertEqual(self.client.get(f"/incidents/{iid}/observations").json(), [])

    def test_invalid_incident_status_location_and_claims(self):
        for change in [{"title": " "}, {"kind": "confirmed_by_ai"}, {"kind": "verified"},
                       {"context": {"latitude": 90}}, {"occurred_at": "2026-10-24T00:00"},
                       {"context": {"origin_ids": ["O1", "O1"]}}, {"unexpected": True}]:
            with self.subTest(change=change):
                self.assertEqual(self.client.post("/incidents", json=incident_body() | change).status_code, 422)
        iid = self.create()
        self.assertEqual(self.client.patch(f"/incidents/{iid}/status", json={"status": "bad"}).status_code, 422)
        self.assertEqual(self.client.get("/incidents?limit=10000").status_code, 422)

    def test_verified_and_user_reported_are_distinct(self):
        body = incident_body() | {"kind": "verified"}
        body["claims"] = [{"kind": "verified", "statement": "Test attribution only", "source": "Test official notice",
                           "observed_at": "2026-10-24T00:00:00Z", "verification_method": "Manual source check (test)"}]
        verified = self.client.post("/incidents", json=body)
        self.assertEqual(verified.status_code, 201)
        body["claims"][0].pop("verification_method")
        self.assertEqual(self.client.post("/incidents", json=body).status_code, 422)
        user = self.client.post("/incidents", json=incident_body() | {"kind": "user_reported"})
        self.assertEqual(user.json()["kind"], "user_reported")

    def test_missing_ids_and_malformed_uuid(self):
        for url in [f"/incidents/{uuid4()}", f"/investigations/{uuid4()}", f"/incidents/{uuid4()}/investigations",
                    f"/investigations/{uuid4()}/recommendations"]:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get("/incidents/not-a-uuid").status_code, 422)

    def test_invalid_closure_requests(self):
        iid = self.create()
        segment = {"id": "X", "u": 1, "v": 2}
        for fields in [{"closures": [segment, segment]}, {"selection": "betweenness", "closures": [segment]},
                       {"closures": [{"id": "X", "u": 1, "v": 1}]}, {"closures": [segment] * 7},
                       {"variable": "wind_direction_10m"}]:
            response = self.client.post(f"/incidents/{iid}/investigations", json=investigation_body() | fields)
            self.assertEqual(response.status_code, 422, response.text)
        user = self.client.post("/incidents", json=incident_body() | {"kind": "user_reported"}).json()["id"]
        self.assertEqual(self.client.post(f"/incidents/{user}/investigations",
                        json=investigation_body() | {"selection": "betweenness"}).status_code, 422)

    def test_failed_tools_are_persisted_without_partial_outputs(self):
        iid = self.create()
        with patch.object(self.app.state.tools, "environment", side_effect=ToolUnavailable("Model cache unavailable")):
            response = self.client.post(f"/incidents/{iid}/investigations", json=investigation_body())
        self.assertEqual(response.status_code, 503, response.text)
        history = self.client.get(f"/incidents/{iid}/investigations").json()
        self.assertEqual(history[0]["status"], "failed")
        self.assertEqual(history[0]["id"], response.json()["detail"]["investigation_id"])
        self.assertIsNone(history[0]["result"])
        self.assertEqual(self.client.get(f"/incidents/{iid}/observations").json(), [])

    def test_unknown_geography_and_segment_rejected(self):
        self.assertEqual(self.client.post("/analysis/geographic", json={"context": {"origin_ids": ["missing"]}}).status_code, 422)
        self.assertEqual(self.client.post("/analysis/geographic", json={"closures": [{"id": "X", "u": -1, "v": -2}]}).status_code, 422)

    def test_analysis_endpoint_contracts_and_openapi(self):
        baseline = self.client.get("/analysis/baseline")
        self.assertEqual(baseline.status_code, 200)
        self.assertEqual(baseline.json()["analysis"]["closures"], [])
        self.assertEqual(baseline.json()["scenario_type"], "hypothetical")
        self.assertEqual(self.client.get("/openapi.json").status_code, 200)
        with patch.object(self.app.state.tools, "environment", side_effect=ToolUnavailable("Live API unavailable")):
            response = self.client.post("/analysis/environment", json=investigation_body())
            # Investigation-only closures are rejected by the standalone environment schema.
            self.assertEqual(response.status_code, 422)
            response = self.client.post("/analysis/environment", json={"as_of": "2026-10-24T19:55:49Z", "mode": "live"})
            self.assertEqual(response.status_code, 503)

    def test_output_transaction_rolls_back_if_recommendation_storage_fails(self):
        iid = self.create()
        with patch("lifelinetwin_backend.main.RecommendationRow", side_effect=RuntimeError("Injected storage failure")):
            with self.assertRaisesRegex(RuntimeError, "Injected storage failure"):
                self.client.post(f"/incidents/{iid}/investigations", json=investigation_body())
        with self.app.state.database.sessions() as session:
            for model in (InvestigationRow, ObservationRow, RecommendationRow):
                self.assertEqual(session.scalar(select(func.count()).select_from(model)), 0)
        self.assertEqual(self.client.get(f"/incidents/{iid}").status_code, 200)

    def test_actual_investigation_persistence_and_provenance(self):
        iid = self.create()
        # No network, no new model: this exercises real cached weather, graph and TTM.
        with patch("socket.socket.connect", side_effect=AssertionError("Network forbidden during cached investigation")):
            response = self.client.post(f"/incidents/{iid}/investigations", json=investigation_body())
        self.assertEqual(response.status_code, 201, response.text)
        saved = response.json()
        result = saved["result"]
        env = result["environment"]
        self.assertEqual(env["forecast"]["forecast_horizon_hours"], 96)
        self.assertEqual(env["forecast"]["model_id"], "ibm-granite/granite-timeseries-ttm-r1")
        cutoff = datetime.fromisoformat(env["provenance"]["context_cutoff_utc"])
        self.assertTrue(all(datetime.fromisoformat(t) <= cutoff for t in env["observations"]["timestamps"]))
        self.assertGreater(env["provenance"]["excluded_future_hours"], 0)
        self.assertFalse(env["provenance"]["weather_implies_road_closure"])
        self.assertEqual(result["geography"]["analysis"]["closures"], [])
        self.assertEqual(result["incident_snapshot"]["kind"], "hypothetical")
        self.assertEqual(result["scenario_memory"]["status"], "verified")
        self.assertEqual(result["scenario_memory"]["roads"], [])
        refs = {e["id"] for e in result["evidence"]}
        self.assertTrue(all(set(r["evidence_refs"]) <= refs for r in result["recommendations"]))
        with self.app.state.database.sessions() as session:
            for model, count in [(InvestigationRow, 1), (ObservationRow, 1), (RecommendationRow, 2)]:
                self.assertEqual(session.scalar(select(func.count()).select_from(model)), count)
        # A separate application and SQLAlchemy engine reads the same file after shutdown/disposal.
        self.client.__exit__(None, None, None)
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.assertEqual(self.client.get(f"/investigations/{saved['id']}").json(), saved)
        self.assertEqual(self.client.get(f"/incidents/{iid}/observations").json()[0]["payload"], env)
        self.assertEqual(len(self.client.get(f"/investigations/{saved['id']}/recommendations").json()), 2)


class ToolIntegrationTests(unittest.TestCase):
    def test_pair_restoration_computed_for_generic_series_bottleneck(self):
        graph = nx.MultiDiGraph()
        graph.add_edge(1, 2, length=10.0)
        graph.add_edge(2, 3, length=10.0)
        origins, facilities = [{"id": "O1", "node": 1}], [{"node": 3}]
        with patch("lifelinetwin_geo.data.load", return_value=(graph, origins, facilities, {})):
            result = Tools(Settings()).geographic(GeographicRequest(closures=[
                {"id": "A", "u": 1, "v": 2}, {"id": "B", "u": 2, "v": 3}]))
        self.assertTrue(all(r["reconnected_origins"] == 0 for r in result.analysis["restorations"]))
        self.assertEqual(result.pair_restorations[0]["reconnected_origins"], 1)
        self.assertEqual(result.pair_restorations[0]["accessibility"][0]["distance_m"], 20.0)
        self.assertEqual(graph.number_of_edges(), 2)

    def test_heidelberg_pair_improvement_matches_direct_graph_calculation(self):
        from lifelinetwin_geo.data import load
        from lifelinetwin_geo.engine import accessibility, close_segments
        old = json.loads((ROOT / "evidence/phase2-5-results.json").read_text(encoding="utf-8"))
        closures = [{k: c[k] for k in ("id", "u", "v")} for c in old["closures"]]
        tools = Tools(Settings())
        result = tools.geographic(GeographicRequest(closures=closures))
        self.assertTrue(result.pair_restorations)
        best = result.pair_restorations[0]
        graph, origins, facilities, _ = load(Settings().geographic_cache)
        direct = accessibility(close_segments(graph, [c for c in closures if c["id"] not in best["reopened"]]), origins, facilities)
        self.assertEqual(best["accessibility"], direct)
        self.assertGreater(best["distance_saved_m_for_already_reachable"], 0)

    def test_missing_model_never_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = Tools(replace(Settings(), model_cache=Path(directory)))
            with patch("socket.socket.connect", side_effect=AssertionError("No download")):
                with self.assertRaisesRegex(ToolUnavailable, "automatic model download is disabled"):
                    tools.environment(EnvironmentRequest(as_of="2026-10-24T19:55:49Z"))

    def test_insufficient_past_context_fails_honestly(self):
        with self.assertRaisesRegex(ToolUnavailable, "512 past hours"):
            Tools(Settings()).environment(EnvironmentRequest(as_of="2026-09-25T00:00:00Z"))

    def test_live_adapter_reuses_ingestion_and_normalizes_timezone(self):
        fixture = json.loads(Settings().weather_snapshot.read_text(encoding="utf-8"))
        with patch("lifelinetwin_geo.weather.fetch_forecast", return_value=fixture) as fetch:
            result = Tools(Settings()).environment(EnvironmentRequest(mode="live", as_of="2026-10-25T00:55:49+05:00"))
        fetch.assert_called_once_with(past_days=30, forecast_days=1)
        self.assertEqual(result.provenance["mode"], "live")
        self.assertIsNone(result.provenance["snapshot_file"])
        self.assertTrue(result.provenance["context_cutoff_utc"].endswith("+00:00"))
        self.assertTrue(result.forecast["metadata"]["context_end"].endswith("+00:00"))

    def test_pairs_not_evaluated_when_single_reopening_has_benefit(self):
        graph = nx.MultiDiGraph()
        graph.add_edge(1, 2, length=1.0)
        graph.add_edge(2, 3, length=1.0)
        graph.add_edge(1, 3, length=10.0)
        graph.add_edge(4, 5, length=1.0)
        with patch("lifelinetwin_geo.data.load", return_value=(graph, [{"id": "O1", "node": 1}], [{"node": 3}], {})):
            result = Tools(Settings()).geographic(GeographicRequest(closures=[
                {"id": "A", "u": 1, "v": 2}, {"id": "B", "u": 4, "v": 5}]))
        self.assertGreater(result.analysis["restorations"][0]["distance_saved_m_for_already_reachable"], 0)
        self.assertEqual(result.pair_restorations, [])


if __name__ == "__main__":
    unittest.main()
