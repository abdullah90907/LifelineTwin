"""Automated unit and integration tests for pretrained time-series forecasting."""
from __future__ import annotations

import math
import unittest
import json
from pathlib import Path

import numpy as np
import torch

from lifelinetwin_geo.forecasting import (
    CONTEXT_LENGTH,
    FORECAST_HORIZON,
    TTMForecaster,
)
from lifelinetwin_geo.weather import get_observations


class ForecastingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forecaster = TTMForecaster()

    def test_input_preparation_context_length_check(self):
        """Must raise ValueError when fewer than 512 context hours are provided."""
        short_vals = [10.0] * 100
        short_times = [f"2026-10-24T{i:02d}:00" for i in range(100)]
        with self.assertRaises(ValueError) as ctx:
            self.forecaster.prepare_input(short_vals, short_times, context_length=512)
        self.assertIn("Context length requirement not met", str(ctx.exception))

    def test_input_preparation_tensor_shape(self):
        """Passes 512 points and verifies tensor shape is (1, 512, 1)."""
        vals = [15.0 + float(i % 10) for i in range(512)]
        times = [f"t_{i}" for i in range(512)]
        tensor, sub_times, meta = self.forecaster.prepare_input(vals, times, context_length=512)

        self.assertEqual(tensor.shape, (1, 512, 1))
        self.assertEqual(len(sub_times), 512)
        self.assertEqual(meta["imputed_count"], 0)
        self.assertEqual(tensor.dtype, torch.float32)

    def test_input_preparation_imputation(self):
        """Verifies None and NaN values are interpolated and counted."""
        vals = [10.0] * 512
        vals[10] = None
        vals[11] = float("nan")
        vals[12] = None
        times = [f"t_{i}" for i in range(512)]

        tensor, _, meta = self.forecaster.prepare_input(vals, times, context_length=512)
        self.assertEqual(meta["imputed_count"], 3)
        self.assertFalse(torch.isnan(tensor).any())

    def test_variable_compatibility_classification(self):
        """Verifies continuous, special, and unsupported classifications."""
        c1 = self.forecaster.check_variable_compatibility("temperature_2m")
        self.assertTrue(c1["supported"])
        self.assertEqual(c1["category"], "continuous")

        c2 = self.forecaster.check_variable_compatibility("precipitation")
        self.assertTrue(c2["supported"])
        self.assertEqual(c2["category"], "special_handling")

        c3 = self.forecaster.check_variable_compatibility("alien_weather_factor")
        self.assertFalse(c3["supported"])
        self.assertEqual(c3["category"], "unsupported")

    def test_persistence_forecast_last_value(self):
        """Verifies last-value persistence replicates the last valid observation."""
        obs = {
            "timestamps": [f"2026-10-24T{i % 24:02d}:00" for i in range(50)],
            "variables": {"temperature_2m": {"values": [10.0] * 49 + [22.5]}},
        }
        res = self.forecaster.predict_persistence(obs, "temperature_2m", horizon=10, mode="last_value")
        self.assertEqual(res["forecast_horizon_hours"], 10)
        self.assertEqual(res["forecast_values"], [22.5] * 10)
        self.assertEqual(res["metadata"]["last_observed_value"], 22.5)

    def test_persistence_forecast_diurnal(self):
        """Verifies diurnal persistence repeats the 24-hour cycle."""
        cycle_24 = [float(i) for i in range(24)]
        obs = {
            "timestamps": [f"2026-10-24T{i:02d}:00" for i in range(24)],
            "variables": {"temperature_2m": {"values": cycle_24}},
        }
        res = self.forecaster.predict_persistence(obs, "temperature_2m", horizon=48, mode="diurnal")
        self.assertEqual(res["forecast_horizon_hours"], 48)
        self.assertEqual(res["forecast_values"][:24], cycle_24)
        self.assertEqual(res["forecast_values"][24:48], cycle_24)


    def test_actual_ttm_model_inference_cpu(self):
        """Runs genuine CPU inference with pretrained IBM Granite TinyTimeMixer."""
        # Use real cached Heidelberg observations
        # Pin the real research snapshot: today/mtime fallback may select a 72-hour cache.
        obs = json.loads((Path(__file__).resolve().parents[1] / "data/heidelberg/weather/obs_forecast_2026-10-24_p30_f7.json").read_text(encoding="utf-8"))
        res = self.forecaster.predict(obs, variable="temperature_2m")

        self.assertEqual(res["model_id"], "ibm-granite/granite-timeseries-ttm-r1")
        self.assertEqual(res["forecast_horizon_hours"], FORECAST_HORIZON)
        self.assertEqual(len(res["forecast_values"]), FORECAST_HORIZON)
        self.assertEqual(len(res["forecast_timestamps"]), FORECAST_HORIZON)
        self.assertEqual(res["metadata"]["inference_device"], "cpu")
        self.assertGreater(res["metadata"]["parameter_count"], 500000)

        # Check all values are valid floats (no NaNs or Infs)
        for val in res["forecast_values"]:
            self.assertIsInstance(val, float)
            self.assertFalse(math.isnan(val))
            self.assertFalse(math.isinf(val))

    def test_precipitation_nonnegativity_clipping(self):
        """Verifies non-negativity clipping prevents negative rainfall predictions."""
        # Pin the real research snapshot: today/mtime fallback may select a 72-hour cache.
        obs = json.loads((Path(__file__).resolve().parents[1] / "data/heidelberg/weather/obs_forecast_2026-10-24_p30_f7.json").read_text(encoding="utf-8"))
        res = self.forecaster.predict(obs, variable="precipitation", clip_nonnegative=True)
        for val in res["forecast_values"]:
            self.assertGreaterEqual(val, 0.0)


if __name__ == "__main__":
    unittest.main()

