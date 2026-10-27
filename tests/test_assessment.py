"""Automated tests for geographic-environmental assessment and routing safety guardrails."""
from __future__ import annotations

import unittest
import json
from pathlib import Path

from lifelinetwin_geo.assessment import (
    assess_environmental_risks,
    generate_environmental_assessment,
)
from lifelinetwin_geo.forecasting import TTMForecaster
from lifelinetwin_geo.weather import STUDY_AREA


class AssessmentTests(unittest.TestCase):
    def test_risk_threshold_triggers_freezing(self):
        """Tests freezing risk indicator detection."""
        risks = assess_environmental_risks(
            current_temp=-1.5,
            forecast_temp_min=-4.0,
            forecast_precip_max_1h=0.0,
            forecast_precip_total=0.0,
            forecast_wind_max=15.0,
        )
        freezing = next(r for r in risks if r["risk"] == "freezing_road_conditions")
        self.assertEqual(freezing["severity"], "high")
        self.assertTrue(freezing["active_now"])
        self.assertTrue(freezing["forecast_event"])

    def test_risk_threshold_triggers_heavy_rain(self):
        """Tests heavy rain threshold detection."""
        risks = assess_environmental_risks(
            current_temp=14.0,
            forecast_temp_min=10.0,
            forecast_precip_max_1h=15.0,  # exceeds 10mm/h threshold
            forecast_precip_total=35.0,   # exceeds 25mm/event threshold
            forecast_wind_max=20.0,
        )
        rain = next(r for r in risks if r["risk"] == "surface_water_pooling_runoff")
        self.assertEqual(rain["severity"], "high")
        self.assertTrue(rain["forecast_event"])

    def test_assessment_structure_and_safety_guardrails(self):
        """Tests that assessment contains all sections and explicitly guarantees routing engine isolation."""
        # Pin the real research snapshot: today/mtime fallback may select a 72-hour cache.
        obs = json.loads((Path(__file__).resolve().parents[1] / "data/heidelberg/weather/obs_forecast_2026-10-24_p30_f7.json").read_text(encoding="utf-8"))
        forecaster = TTMForecaster()
        fc = forecaster.predict(obs, variable="temperature_2m")

        assessment = generate_environmental_assessment(obs, forecast=fc, study_area=STUDY_AREA)

        # 1. Structure
        self.assertEqual(assessment["assessment_type"], "GeographicEnvironmentalAssessment")
        self.assertIn("study_area", assessment)
        self.assertEqual(assessment["study_area"]["name"], STUDY_AREA["name"])
        self.assertIn("observation_summary", assessment)
        self.assertIn("forecast_summary", assessment)
        self.assertIn("environmental_risk_indicators", assessment)
        self.assertIn("geospatial_infrastructure_context", assessment)
        self.assertIn("evidence", assessment)

        # 2. Strict Safety Guardrail: Routing engine unaffected
        geo_ctx = assessment["geospatial_infrastructure_context"]
        self.assertTrue(geo_ctx["routing_engine_unaffected"])
        self.assertIn("NEVER automatically closed", geo_ctx["policy_isolation_statement"])
        self.assertIn("UNMODIFIED", geo_ctx["policy_isolation_statement"])


if __name__ == "__main__":
    unittest.main()

