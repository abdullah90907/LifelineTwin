"""Offline reliability tests only. All SDK requests are mocked; no live provider calls."""
import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import httpx
from openai import RateLimitError, APIStatusError, APITimeoutError, APIConnectionError
from sqlalchemy import select, func
from lifelinetwin_backend.agent_limits import _worker, bounded_call, ExecutionLimit
from lifelinetwin_backend.agent_failures import FailureMetadata, ProviderFailure, classify_exception, parse_retry_after
from lifelinetwin_backend.agent import AgentRunner
from lifelinetwin_backend.agent_schemas import AgentRequest
from lifelinetwin_backend.config import Settings
from lifelinetwin_backend.database import Database, IncidentRow
from lifelinetwin_backend.schemas import Incident
from lifelinetwin_backend.agent_storage import AgentRunRow, AgentTraceRow
from lifelinetwin_backend.agent_provider import ProviderConfig, OpenAICompatibleProvider
from pydantic import SecretStr
from _reliability_fixtures import raise_rate_limit


class CapturePipe:
    def __init__(self):
        self.payload = None

    def send(self, payload):
        self.payload = payload

    def close(self):
        pass


class FailureBoundaryTests(unittest.TestCase):
    def test_worker_preserves_sanitized_http_classification(self):
        pipe = CapturePipe()
        _worker(pipe, raise_rate_limit, ())
        failure = pipe.payload["failure"]
        self.assertEqual(failure["http_status"], 429)
        self.assertEqual(failure["category"], "rate_limit")
        self.assertEqual(failure["provider_code"], "rate_limit_exceeded")
        self.assertEqual(failure["request_id"], "req_offline_123")
        self.assertEqual(failure["retry_after_seconds"], 2)
        self.assertNotIn("SENSITIVE", str(pipe.payload))

    def test_worker_drops_exception_messages_and_arbitrary_body_fields(self):
        pipe = CapturePipe()
        _worker(pipe, raise_rate_limit, ())
        self.assertIn("failure", pipe.payload)
        self.assertNotIn("message", pipe.payload["failure"])
        self.assertNotIn("body", pipe.payload["failure"])

    def test_real_spawn_boundary_keeps_classification(self):
        with self.assertRaises(ProviderFailure) as caught:
            bounded_call(raise_rate_limit, (), 30)
        self.assertEqual(caught.exception.metadata.category, "rate_limit")
        self.assertEqual(caught.exception.metadata.request_id, "req_offline_123")
        self.assertNotIn("SENSITIVE", str(caught.exception))

    def test_real_sdk_mock_transport_has_no_hidden_retries_or_sensitive_failure_body(self):
        from openai import OpenAI as RealClient
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(429, headers={"x-request-id":"req_mock_sdk", "retry-after":"0"},
                json={"error":{"code":"rate_limit_exceeded","message":"SENSITIVE PROMPT BODY"}})
        def client(**kwargs):
            return RealClient(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        provider = OpenAICompatibleProvider(ProviderConfig("configured-model", "https://never-contact.invalid/v1", SecretStr("test-only-secret")))
        pipe = CapturePipe()
        with patch("openai.OpenAI",side_effect=client):
            _worker(pipe, provider.complete, ([{"role":"user","content":"SENSITIVE REQUEST PROMPT"}], [], 5))
        self.assertEqual(len(requests),1)
        self.assertEqual(pipe.payload["failure"]["request_id"],"req_mock_sdk")
        self.assertEqual(pipe.payload["failure"]["category"],"rate_limit")
        self.assertNotIn("SENSITIVE",json.dumps(pipe.payload))
        self.assertNotIn("test-only-secret",json.dumps(pipe.payload))


def status_error(status, code=None, retry_after=None, request_id="req_offline_123"):
    headers = {"x-request-id": request_id}
    if retry_after is not None:
        headers["retry-after"] = retry_after
    return APIStatusError("SENSITIVE RAW PROMPT", response=httpx.Response(status, headers=headers,
        request=httpx.Request("POST", "https://never-contact.invalid/v1")),
        body={"error": {"code": code, "message": "SENSITIVE BODY", "failed_generation": "SENSITIVE PROMPT"}})


class ClassificationTests(unittest.TestCase):
    def test_http_categories_and_permanent_no_retry(self):
        cases = [(429, "rate_limit_exceeded", "rate_limit", True),
                 (429, "insufficient_quota", "rate_limit", False),
                 (429, None, "rate_limit", False),
                 (503, "server_error", "service_failure", True),
                 (502, None, "service_failure", True),
                 (500, None, "service_failure", True),
                 (504, None, "service_failure", True),
                 (501, None, "provider_request", False),
                 (400, "tool_use_failed", "malformed_tool_call", False),
                 (400, "context_length_exceeded", "provider_request", False),
                 (401, "invalid_api_key", "authentication", False),
                 (403, "permission_denied", "authentication", False)]
        for status, code, category, transient in cases:
            with self.subTest(status=status, code=code):
                metadata = classify_exception(status_error(status, code))
                self.assertEqual(metadata.category, category)
                self.assertEqual(metadata.transient, transient)

    def test_timeout_and_transport_are_distinct_and_not_retried(self):
        request = httpx.Request("POST", "https://never-contact.invalid")
        for error, category in [(APITimeoutError(request), "timeout"),
                                (APIConnectionError(request=request), "transport"),
                                (httpx.ReadTimeout("SENSITIVE"), "timeout"),
                                (httpx.ConnectError("SENSITIVE"), "transport")]:
            metadata = classify_exception(error)
            self.assertEqual(metadata.category, category)
            self.assertFalse(metadata.transient)

    def test_retry_after_numeric_http_date_and_invalid(self):
        wall = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(parse_retry_after("2.5"), 2.5)
        self.assertEqual(parse_retry_after("Sun, 25 Oct 2026 00:00:03 GMT", wall), 3)
        self.assertEqual(parse_retry_after("Sun, 25 Oct 2026 00:00:00 GMT", wall), 0)
        for value in ("nan", "inf", "-1", "invalid", "9999999999999999999"):
            self.assertIsNone(parse_retry_after(value))

    def test_unknown_codes_sensitive_headers_and_bodies_are_not_serialized(self):
        metadata = classify_exception(status_error(429, "SENSITIVE_CODE", "SENSITIVE_HEADER", "Bearer SENSITIVE_TOKEN"))
        encoded = metadata.model_dump_json()
        self.assertNotIn("SENSITIVE", encoded)
        self.assertIsNone(metadata.provider_code)
        self.assertIsNone(metadata.request_id)
        self.assertIsNone(metadata.retry_after_seconds)
        self.assertTrue(metadata.retry_after_supplied)


def response(name="retrieve_incident", args=None, cid="call1"):
    return {"model": "offline-test-only", "note": "", "request_id": "req_offline_response",
            "calls": [{"id": cid, "name": name, "arguments": json.dumps(args or {})}]}


def final_response(eid="E1"):
    citation = {"evidence_id": eid, "pointer": "/kind"}
    return response("complete_investigation", {"findings": [citation], "uncertainties": ["road_status_unverified"],
        "actions": [{"kind": "verify_road_status", "citations": [citation]}]})


class RunnerReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "reliability.sqlite3")
        self.db.initialize()
        with self.db.sessions.begin() as session:
            row = IncidentRow(payload={"title": "Offline test", "description": "Hypothetical only", "kind": "hypothetical",
                "occurred_at": "2026-10-24T19:55:49Z", "context": {}, "claims": []})
            session.add(row)
            session.flush()
            self.incident = Incident(**row.payload, id=row.id, status=row.status, created_at=row.created_at, updated_at=row.updated_at)
        self.provider = SimpleNamespace(identity={"live_llm": False, "adapter": "controlled_test"}, secret="test-only-secret")

    def tearDown(self):
        self.db.engine.dispose()
        self.temp.cleanup()

    def run_case(self, responses, tool_output=None, tool_failure=None, **options):
        request = AgentRequest(question="Offline reliability test", as_of="2026-10-24T19:55:49Z", **options)
        runner = AgentRunner(self.db, Settings(), self.incident, request, self.provider)
        output = tool_output or ("attributed_incident_claims", {"kind": "hypothetical"})
        with patch("lifelinetwin_backend.agent.bounded_call", side_effect=responses) as provider, \
             patch.object(runner.tools, "execute", return_value=output, side_effect=tool_failure) as analytical, \
             patch("lifelinetwin_backend.agent.time.sleep") as sleep:
            result = runner.run()
        with self.db.sessions() as session:
            row = session.get(AgentRunRow, result.id)
            self.checkpoint = row.checkpoint
            self.trace = [{"kind": r.kind, "payload": r.payload, "sequence": r.sequence}
                          for r in session.scalars(select(AgentTraceRow).where(AgentTraceRow.run_id == result.id).order_by(AgentTraceRow.sequence))]
        return result, provider, analytical, sleep

    def test_transient_retry_preserves_accepted_evidence_and_identical_prompt(self):
        result, provider, analytical, sleep = self.run_case([response(),
            ProviderFailure(classify_exception(status_error(429, "rate_limit_exceeded", "2"))), final_response()])
        self.assertEqual(result.status, "completed")
        self.assertEqual(provider.call_count, 3)
        self.assertEqual(analytical.call_count, 1)
        sleep.assert_called_once_with(2)
        self.assertEqual(provider.call_args_list[1].args[1][1], provider.call_args_list[2].args[1][1])
        self.assertEqual(result.result.findings[0].value, "hypothetical")
        self.assertEqual(self.checkpoint["provider_attempts"], 3)
        self.assertTrue(self.checkpoint["retry_used"])
        self.assertEqual(len(self.checkpoint["evidence"]), 2)
        failure = next(e["payload"] for e in self.trace if e["kind"] == "provider_failure")
        self.assertEqual(failure["agent_step"], 2)
        self.assertEqual(failure["http_status"], 429)
        self.assertTrue(failure["retry_scheduled"])
        self.assertEqual(self.checkpoint["evidence"]["E1"]["data"], {"kind": "hypothetical"})
        self.assertEqual([t["sequence"] for t in self.trace], list(range(1,len(self.trace)+1)))

    def test_one_retry_for_entire_run_not_per_step(self):
        transient = ProviderFailure(classify_exception(status_error(503, "server_error")))
        result, provider, analytical, sleep = self.run_case([transient, response(), transient])
        self.assertEqual(result.status, "failed")
        self.assertEqual(provider.call_count, 3)
        self.assertEqual(analytical.call_count, 1)
        self.assertEqual(sleep.call_count, 1)
        failures = [t["payload"] for t in self.trace if t["kind"] == "provider_failure"]
        self.assertEqual(failures[-1]["retry_decision"], "run_retry_already_used")
        self.assertIn("E1", self.checkpoint["evidence"])

    def test_retry_does_not_expand_attempt_or_token_budget(self):
        transient = ProviderFailure(classify_exception(status_error(503)))
        result, provider, _, sleep = self.run_case([transient], max_iterations=1)
        self.assertEqual(result.status, "failed")
        self.assertEqual(provider.call_count, 1)
        sleep.assert_not_called()
        result, provider, _, sleep = self.run_case([transient, transient], max_iterations=2)
        self.assertEqual(provider.call_count, 2)
        self.assertEqual(result.status, "failed")

    def test_long_invalid_or_unaffordable_retry_after_is_not_shortened(self):
        for value, timeout in [("60",120), ("nan",120), ("5",5)]:
            with self.subTest(value=value):
                failure = ProviderFailure(classify_exception(status_error(429, "rate_limit_exceeded", value)))
                result, provider, _, sleep = self.run_case([failure], timeout_seconds=timeout)
                self.assertEqual(provider.call_count, 1)
                self.assertEqual(result.status, "failed")
                sleep.assert_not_called()

    def test_permanent_sdk_failures_have_no_retry(self):
        errors = [status_error(401,"invalid_api_key"), status_error(400,"tool_use_failed"),
                  status_error(429,"insufficient_quota"), APITimeoutError(httpx.Request("POST","https://no.invalid")),
                  APIConnectionError(request=httpx.Request("POST","https://no.invalid"))]
        for error in errors:
            result, provider, _, sleep = self.run_case([ProviderFailure(classify_exception(error))])
            self.assertEqual(result.status, "failed")
            self.assertEqual(provider.call_count, 1)
            sleep.assert_not_called()

    def test_parent_worker_timeout_is_classified_without_retry(self):
        result, provider, analytical, sleep = self.run_case([ExecutionLimit("SENSITIVE TIMEOUT")])
        self.assertEqual(result.status, "limited")
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(analytical.call_count, 0)
        sleep.assert_not_called()
        failure = next(e["payload"] for e in self.trace if e["kind"] == "provider_failure")
        self.assertEqual(failure["category"], "timeout")
        self.assertEqual(failure["stage"], "provider_worker")

    def test_malformed_call_has_no_retry_or_analytical_execution(self):
        invalid = response()
        invalid["calls"][0]["arguments"] = "{not-json"
        result, provider, analytical, sleep = self.run_case([invalid])
        self.assertEqual(result.status, "failed")
        self.assertEqual(analytical.call_count, 0)
        self.assertEqual(provider.call_count, 1)
        sleep.assert_not_called()
        failure = next(e["payload"] for e in self.trace if e["kind"] == "provider_failure")
        self.assertEqual(failure["category"], "malformed_tool_call")
        self.assertEqual(failure["request_id"], "req_offline_response")

    def test_invalid_agent_response_is_distinct(self):
        result, provider, analytical, sleep = self.run_case([{"unexpected": "SENSITIVE PROMPT"}])
        self.assertEqual(result.status, "failed")
        failure = next(e["payload"] for e in self.trace if e["kind"] == "provider_failure")
        self.assertEqual(failure["category"], "invalid_agent_output")
        self.assertNotIn("SENSITIVE", json.dumps(self.trace))

    def test_invalid_tool_arguments_and_invalid_final_output_not_auto_retried(self):
        for call, category in [(response(args={"unknown":1}),"invalid_tool_arguments"),
                               (response("complete_investigation",{"findings":[]}),"invalid_tool_arguments")]:
            result, provider, analytical, sleep = self.run_case([call], max_iterations=1)
            self.assertEqual(provider.call_count,1)
            self.assertEqual(analytical.call_count,0)
            sleep.assert_not_called()
            failure = next(e["payload"]["failure"] for e in self.trace if e["kind"]=="tool")
            self.assertEqual(failure["category"],category)
        # Well-shaped final selection with an unsupported evidence reference.
        result, provider, analytical, sleep = self.run_case([final_response("missing")],max_iterations=1)
        failure = next(e["payload"]["failure"] for e in self.trace if e["kind"]=="tool")
        self.assertEqual(failure["category"],"invalid_agent_output")

    def test_duplicate_success_uses_same_evidence_without_reexecution_or_payload_rewrite(self):
        result, provider, analytical, _ = self.run_case([response(cid="a"), response(cid="b"), final_response()])
        self.assertEqual(result.status,"completed")
        self.assertEqual(analytical.call_count,1)
        tools=[t["payload"] for t in self.trace if t["kind"]=="tool"]
        self.assertEqual(len(tools),2)
        self.assertEqual(tools[0]["evidence_id"],tools[1]["evidence_id"])
        self.assertFalse(tools[0]["reused"])
        self.assertTrue(tools[1]["reused"])
        self.assertIsNone(tools[1]["output"])
        self.assertEqual(len(self.checkpoint["evidence"]),2)
        with self.db.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(AgentRunRow)),1)

    def test_assembled_raw_prompt_not_in_failure_trace_or_checkpoint(self):
        with patch("lifelinetwin_backend.agent.SYSTEM", "SENSITIVE ASSEMBLED PROMPT"):
            result, _, _, _ = self.run_case([ProviderFailure(classify_exception(status_error(401,"invalid_api_key")))])
        self.assertNotIn("SENSITIVE",json.dumps(self.trace)+json.dumps(self.checkpoint))
        self.assertNotIn("messages",self.checkpoint)
        self.assertNotIn(b"SENSITIVE",(Path(self.temp.name)/"reliability.sqlite3").read_bytes())

    def test_duplicate_failed_tool_is_not_executed_again(self):
        result, _, analytical, _ = self.run_case([response(cid="a"),response(cid="b"),final_response("E0")],
                                               tool_failure=RuntimeError("SENSITIVE FAILURE"))
        self.assertEqual(result.status,"completed")
        self.assertEqual(analytical.call_count,1)
        self.assertEqual(set(self.checkpoint["evidence"]),{"E0"})
        self.assertNotIn("SENSITIVE",json.dumps(self.trace))
        repeated=[t["payload"] for t in self.trace if t["kind"]=="tool"]
        self.assertTrue(repeated[1]["reused"])

    def test_failure_metadata_and_accepted_evidence_survive_database_reopen(self):
        transient = ProviderFailure(classify_exception(status_error(503,"server_error","0")))
        result, _, _, _ = self.run_case([response(),transient,final_response()])
        self.db.engine.dispose()
        self.db = Database(Path(self.temp.name)/"reliability.sqlite3")
        self.db.initialize()
        with self.db.sessions() as session:
            saved = session.get(AgentRunRow,result.id)
            self.assertEqual(saved.status,"completed")
            self.assertEqual(saved.result,result.result.model_dump(mode="json"))
            self.assertEqual(saved.checkpoint["evidence"]["E1"]["data"],{"kind":"hypothetical"})
            traces = list(session.scalars(select(AgentTraceRow).where(AgentTraceRow.run_id==result.id)))
            failure = next(t.payload for t in traces if t.kind=="provider_failure")
            self.assertEqual(failure["request_id"],"req_offline_123")
            self.assertEqual(failure["http_status"],503)

    def test_normalized_closure_order_uses_one_analytical_result(self):
        approved=[{"id":"A","u":1,"v":2},{"id":"B","u":3,"v":4}]
        result, _, analytical, _ = self.run_case([
            response("analyze_closures",{"closure_ids":["A","B"]},"a"),
            response("analyze_closures",{"closure_ids":["B","A"]},"b"),final_response()],allowed_closures=approved)
        self.assertEqual(result.status,"completed")
        self.assertEqual(analytical.call_count,1)

    def test_empty_sdk_choices_classifies_invalid_output_and_keeps_request_id(self):
        provider = OpenAICompatibleProvider(ProviderConfig("configured-model","https://no-network.invalid/v1",SecretStr("test-only")))
        with patch("openai.OpenAI") as sdk:
            sdk.return_value.__enter__.return_value.chat.completions.create.return_value = SimpleNamespace(choices=[],_request_id="req_empty_output")
            with self.assertRaises(ProviderFailure) as caught:
                provider.complete([],[],1)
        self.assertEqual(caught.exception.metadata.category,"invalid_agent_output")
        self.assertEqual(caught.exception.metadata.request_id,"req_empty_output")


if __name__ == "__main__":
    unittest.main()
