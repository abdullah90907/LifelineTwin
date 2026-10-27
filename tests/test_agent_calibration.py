"""Phase 4E offline calibration; controlled providers are not live-success evidence."""
import json
import os
import unittest
from unittest.mock import patch

from lifelinetwin_backend.agent_context import ContextPolicy, fits, request_metrics, UsageWindow
from lifelinetwin_backend.agent_provider import ProviderConfig
from scripts.calibrate_context_budget import audit
from _phase4d_fixtures import AdaptiveEvidenceProvider, call
import test_agent_optimization as optimization


class SequentialEvidenceProvider(AdaptiveEvidenceProvider):
    """Reproduce the six live tool choices, then inspect real evidence and finish.

    A test fixture only. Decisions after the initial sequence depend on the
    actual catalog and inspection results, using the existing adaptive fixture.
    """
    def complete(self, messages, tools, timeout):
        step = sum(m['role'] == 'assistant' for m in messages)
        sequence = ['retrieve_incident', 'analyze_closures', 'retrieve_observations',
                    'baseline_accessibility', 'retrieve_incident', 'generate_forecast']
        if step >= len(sequence):
            return super().complete(messages, tools, timeout)
        initial = json.loads(messages[1]['content'])
        name = sequence[step]
        args = {'closure_ids': [c['id'] for c in initial['allowed_hypothetical_closures']]} if name == 'analyze_closures' else {}
        return {'model': 'controlled-offline-not-live', 'note': 'Controlled sequential tool selection.',
                'calls': [call(name, args, 'sequential_' + str(step))]}


class CalibrationTests(unittest.TestCase):
    def test_saved_usage_remains_conservatively_overestimated(self):
        data = audit()
        self.assertEqual(len(data['usage_samples']), 6)
        self.assertTrue(all(1.7 < row['ratio'] < 1.85 for row in data['usage_samples']))
        self.assertEqual(data['live_requests'], 0)

    def test_saved_failure_replays_and_now_fits_without_changing_evidence(self):
        rows = audit()['replay']
        self.assertEqual(len(rows), 7)
        self.assertFalse(rows[-1]['old']['admitted'])
        self.assertEqual(rows[-1]['old']['estimated_input_tokens'], 3653)
        self.assertEqual(rows[-1]['old']['request_bytes'], 10142)
        self.assertTrue(rows[-1]['new']['admitted'])
        # Extra headroom also preserves a richer most-recent exchange.
        self.assertGreater(rows[-1]['new']['request_bytes'], rows[-1]['old']['request_bytes'])
        self.assertLessEqual(rows[-1]['new']['request_bytes'], 12000)

    def test_shared_defaults_and_explicit_operator_ceiling(self):
        env = {'LIFELINETWIN_LLM_MODEL': 'configured', 'LIFELINETWIN_LLM_BASE_URL': 'https://no.invalid/v1',
               'LIFELINETWIN_LLM_API_KEY': 'test-only'}
        with patch.dict(os.environ, env, clear=True):
            config = ProviderConfig.from_environment()
            self.assertEqual(config.max_input_tokens, ContextPolicy().max_input_tokens)
            self.assertEqual(config.max_input_tokens, 4200)
            os.environ['LIFELINETWIN_LLM_MAX_INPUT_TOKENS'] = '3500'
            self.assertEqual(ProviderConfig.from_environment().max_input_tokens, 3500)

    def test_token_and_byte_edges_are_inclusive_and_independent(self):
        metric = request_metrics([{'role': 'user', 'content': 'A measurable question'}], [])
        metric.update(max_input_tokens=metric['estimated_input_tokens'], max_request_bytes=metric['request_bytes'])
        self.assertTrue(fits(metric))
        self.assertFalse(fits({**metric, 'max_input_tokens': metric['estimated_input_tokens'] - 1}))
        self.assertFalse(fits({**metric, 'max_request_bytes': metric['request_bytes'] - 1}))
        oversize = request_metrics([{'role': 'user', 'content': '道' * 4100}], [], policy=ContextPolicy(max_input_tokens=32000))
        self.assertGreater(oversize['request_bytes'], 12000)
        self.assertFalse(fits(oversize))

    def test_retained_estimator_reserves_output_even_without_usage(self):
        metric = request_metrics([{'role': 'user', 'content': 'x' * 10000}], [])
        self.assertEqual(metric['estimated_reserved_tokens'], metric['estimated_input_tokens'] + 1800)
        self.assertEqual(metric['token_count_method'], 'utf8_bytes_divided_by_3_plus_framing_estimate')
        meter = UsageWindow(metric['estimated_reserved_tokens'])
        row = meter.reserve(metric['estimated_reserved_tokens'], 0)
        meter.reconcile(row, {})
        self.assertEqual(meter.wait_required(1, 1), 59)
        self.assertEqual(meter.wait_required(metric['estimated_reserved_tokens'] + 1, 60), float('inf'))

    def test_eight_round_real_tools_inspection_completion_and_restart(self):
        harness = optimization.RealAnalyticalIntegrationTests()
        saved, trace, checkpoint = harness.run_case(
            'Compare approved geographic disruptions with environmental evidence and forecast; inspect source details.',
            provider_factory=SequentialEvidenceProvider, max_iterations=10)
        self.assertEqual(saved['iterations'], 8)
        names = [t['payload']['tool'] for t in trace if t['kind'] == 'tool']
        self.assertEqual(names[:6], ['retrieve_incident', 'analyze_closures', 'retrieve_observations',
                                    'baseline_accessibility', 'retrieve_incident', 'generate_forecast'])
        repeat = [t['payload'] for t in trace if t['kind'] == 'tool' and t['payload']['tool'] == 'retrieve_incident']
        self.assertTrue(repeat[1]['reused'])
        self.assertEqual(repeat[0]['evidence_id'], repeat[1]['evidence_id'])
        self.assertFalse(any(t['kind'] == 'provider_retry' for t in trace))
        self.assertNotIn('messages', checkpoint)
        print(json.dumps({'phase4e_controlled_only': True, 'status': saved['status'],
            'rounds': saved['iterations'], 'tool_calls': saved['tool_calls'],
            'peak_bytes': max(m['request_bytes'] for m in checkpoint['context_metrics']),
            'peak_estimate': max(m['estimated_input_tokens'] for m in checkpoint['context_metrics']),
            'exact_citations_and_restart_equal': True}))


if __name__ == '__main__':
    unittest.main()
