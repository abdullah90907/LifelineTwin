"""Automated tests for forecast validation and metric calculation."""
from __future__ import annotations

import math
import unittest
import json
from pathlib import Path

from lifelinetwin_geo.evaluation import (
    calculate_metrics,
    evaluate_forecast,
)
from lifelinetwin_geo.weather import get_observations


class EvaluationTests(unittest.TestCase):
    def test_calculate_metrics_exact_values(self):
        """Verifies calculation of MAE, RMSE, and bias against exact hand-calculated values."""
        preds = [10.0, 12.0, 14.0, 16.0]
        actuals = [8.0, 12.0, 15.0, 19.0]
        # Errors (preds - actuals): [+2.0, 0.0, -1.0, -3.0]
        # Absolute errors: [2.0, 0.0, 1.0, 3.0] -> sum=6.0 -> mean=1.5
        # Squared errors: [4.0, 0.0, 1.0, 9.0] -> sum=14.0 -> mean=3.5 -> sqrt(3.5)=1.8708
        # Bias: (2 + 0 - 1 - 3) / 4 = -2 / 4 = -0.5
        res = calculate_metrics(preds, actuals)
        self.assertEqual(res["count"], 4)
        self.assertEqual(res["mae"], 1.5)
        self.assertAlmostEqual(res["rmse"], math.sqrt(3.5), places=3)
        self.assertEqual(res["bias"], -0.5)
        self.assertEqual(res["status"], "ok")

    def test_calculate_metrics_nan_and_none_filtering(self):
        """Pairs with NaN or None are excluded without errors."""
        preds = [10.0, None, float("nan"), 12.0]
        actuals = [8.0, 10.0, 14.0, 12.0]
        # Only pairs (10, 8) and (12, 12) are valid -> errors [+2.0, 0.0]
        res = calculate_metrics(preds, actuals)
        self.assertEqual(res["count"], 2)
        self.assertEqual(res["mae"], 1.0)
        self.assertEqual(res["bias"], 1.0)

    def test_calculate_metrics_length_mismatch(self):
        with self.assertRaises(ValueError):
            calculate_metrics([1.0, 2.0], [1.0])

    def test_evaluate_forecast_historical_backtest(self):
        """Runs full evaluation pipeline on authentic cached observations and validates outputs."""
        # Pin the real research snapshot: today/mtime fallback may select a 72-hour cache.
        obs = json.loads((Path(__file__).resolve().parents[1] / "data/heidelberg/weather/obs_forecast_2026-10-24_p30_f7.json").read_text(encoding="utf-8"))
        ev = evaluate_forecast(obs, variable="temperature_2m", horizon=96, context_length=512)

        self.assertEqual(ev["variable"], "temperature_2m")
        self.assertEqual(ev["unit"], "degC")
        self.assertEqual(ev["evaluation_window"]["horizon_hours"], 96)

        # Check all models were computed
        models = ev["models"]
        self.assertIn("ibm_granite_ttm_r1", models)
        self.assertIn("persistence_diurnal", models)
        self.assertIn("persistence_last_value", models)

        # Metrics must be positive real numbers
        ttm_m = models["ibm_granite_ttm_r1"]["metrics"]
        self.assertEqual(ttm_m["count"], 96)
        self.assertGreater(ttm_m["mae"], 0.0)
        self.assertGreater(ttm_m["rmse"], 0.0)

        # Comparison must contain non-null values
        self.assertIsNotNone(ev["comparison"]["best_by_mae"])
        self.assertIsInstance(ev["comparison"]["ttm_vs_last_value_mae_diff"], float)


if __name__ == "__main__":
    unittest.main()

