"""Pretrained time-series forecasting using IBM Granite TinyTimeMixer (TTM).

Integrates the official lightweight IBM Granite TinyTimeMixer (TTM-R1) from
Hugging Face (`ibm-granite/granite-timeseries-ttm-r1`) via tsfm_public.
Runs exclusively on CPU without model training or fine-tuning.
Provides rigorous input preparation, context length validation, missing value
imputation, variable suitability checking, and baseline persistence forecasting.
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import torch

from .weather import VARIABLE_UNITS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MODEL_ID = "ibm-granite/granite-timeseries-ttm-r1"
CONTEXT_LENGTH = 512
FORECAST_HORIZON = 96  # 4 days of hourly predictions

# Model suitability classifications
CONTINUOUS_VARIABLES = [
    "temperature_2m",
    "surface_pressure",
    "wind_speed_10m",
    "relative_humidity_2m",
]

SPECIAL_VARIABLES = {
    "precipitation": (
        "Zero-inflated intermittent variable. TTM can infer continuous trends, "
        "but raw outputs require zero-clipping. Persistence / climatological baselines "
        "should be compared alongside model outputs."
    ),
    "wind_direction_10m": (
        "Circular variable (0-360 degrees). Standard continuous MSE loss does not "
        "respect modular wrap-around (359 deg and 1 deg are 2 deg apart). "
        "Circular baseline or wind vector decomposition is recommended."
    ),
}


class TTMForecaster:
    """CPU-based inference engine for IBM Granite TinyTimeMixer."""

    def __init__(self, model_id: str = DEFAULT_MODEL_ID):
        self.model_id = model_id
        self._model = None
        self._param_count = None

    def load_model(self) -> Any:
        """Load the pretrained TTM model in evaluation mode on CPU."""
        if self._model is not None:
            return self._model

        from tsfm_public import TinyTimeMixerForPrediction

        model = TinyTimeMixerForPrediction.from_pretrained(self.model_id)
        model.eval()
        self._model = model
        self._param_count = sum(p.numel() for p in model.parameters())
        return self._model

    @property
    def param_count(self) -> int:
        if self._param_count is None:
            self.load_model()
        return self._param_count  # type: ignore

    def check_variable_compatibility(self, variable: str) -> dict[str, Any]:
        """Check whether a meteorological variable is suitable for continuous TTM."""
        if variable in CONTINUOUS_VARIABLES:
            return {
                "variable": variable,
                "supported": True,
                "category": "continuous",
                "notes": "Fully supported for continuous foundation model forecasting.",
            }
        if variable in SPECIAL_VARIABLES:
            return {
                "variable": variable,
                "supported": True,
                "category": "special_handling",
                "notes": SPECIAL_VARIABLES[variable],
            }
        return {
            "variable": variable,
            "supported": False,
            "category": "unsupported",
            "notes": f"Variable '{variable}' is not recognized in standard environmental profile.",
        }

    def prepare_input(
        self,
        values: list[float | None],
        timestamps: list[str],
        context_length: int = CONTEXT_LENGTH,
    ) -> tuple[torch.Tensor, list[str], dict[str, Any]]:
        """Validate and format a raw observation series into a TTM input tensor.

        Returns (input_tensor of shape (1, context_length, 1), context_timestamps, metadata).
        Raises ValueError if fewer than context_length values are available.
        """
        if len(values) < context_length:
            raise ValueError(
                f"Context length requirement not met: series has {len(values)} hours, "
                f"but TTM requires at least {context_length} hours of context."
            )
        if len(timestamps) != len(values):
            raise ValueError("Timestamps and values lengths do not match.")

        # Slice the most recent context_length points
        sub_vals = values[-context_length:]
        sub_times = timestamps[-context_length:]

        # Handle missing / NaN values with linear interpolation and forward/backward fill
        clean_vals: list[float] = []
        imputed_count = 0

        # Pass 1: detect and mark
        numeric_series = []
        for v in sub_vals:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                numeric_series.append(np.nan)
                imputed_count += 1
            else:
                numeric_series.append(float(v))

        arr = np.array(numeric_series, dtype=np.float32)
        if np.isnan(arr).all():
            raise ValueError("All context values are NaN or None.")

        # Interpolate
        nans = np.isnan(arr)
        if np.any(nans):
            x = np.arange(len(arr))
            arr[nans] = np.interp(x[nans], x[~nans], arr[~nans])

        # Shape: (batch_size=1, sequence_length=context_length, num_channels=1)
        tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(-1)

        meta = {
            "context_length": context_length,
            "context_start": sub_times[0],
            "context_end": sub_times[-1],
            "imputed_count": imputed_count,
            "raw_min": float(np.min(arr)),
            "raw_max": float(np.max(arr)),
            "raw_mean": float(np.mean(arr)),
        }
        return tensor, sub_times, meta

    def generate_future_timestamps(self, last_timestamp: str, horizon: int) -> list[str]:
        """Produce horizon hourly timestamps starting from last_timestamp + 1 hour."""
        try:
            dt = datetime.fromisoformat(last_timestamp.replace("Z", "+00:00"))
            return [(dt + timedelta(hours=i + 1)).isoformat() for i in range(horizon)]
        except (ValueError, TypeError):
            return [f"{last_timestamp}+{i + 1}h" for i in range(horizon)]


    def predict(
        self,
        observations: dict[str, Any],
        variable: str = "temperature_2m",
        clip_nonnegative: bool | None = None,
    ) -> dict[str, Any]:
        """Generate short-term pretrained forecasts for a supported variable.

        Uses IBM Granite TinyTimeMixer on CPU.
        """
        compat = self.check_variable_compatibility(variable)
        if not compat["supported"]:
            raise ValueError(f"Incompatible variable for TTM forecasting: {variable}. {compat['notes']}")

        var_entry = observations.get("variables", {}).get(variable)
        if not var_entry:
            raise KeyError(f"Variable '{variable}' not found in observations dictionary.")

        raw_values = var_entry.get("values", [])
        timestamps = observations.get("timestamps", [])

        input_tensor, ctx_times, meta = self.prepare_input(raw_values, timestamps, CONTEXT_LENGTH)

        model = self.load_model()
        t0 = time.perf_counter()
        with torch.no_grad():
            out = model(past_values=input_tensor)
        inference_time_ms = round((time.perf_counter() - t0) * 1000, 2)

        preds = out.prediction_outputs[0, :, 0].cpu().numpy().tolist()

        # For precipitation, enforce non-negativity
        if clip_nonnegative is None:
            clip_nonnegative = (variable == "precipitation")
        if clip_nonnegative:
            preds = [max(0.0, float(p)) for p in preds]
        else:
            preds = [float(p) for p in preds]

        future_times = self.generate_future_timestamps(ctx_times[-1], len(preds))

        return {
            "model_id": self.model_id,
            "method": "ttm_pretrained_zeroshot",
            "variable": variable,
            "unit": VARIABLE_UNITS.get(variable, var_entry.get("unit", "")),
            "context_length_hours": CONTEXT_LENGTH,
            "forecast_horizon_hours": len(preds),
            "forecast_timestamps": future_times,
            "forecast_values": preds,
            "variable_compatibility": compat,
            "metadata": {
                **meta,
                "inference_device": "cpu",
                "inference_time_ms": inference_time_ms,
                "parameter_count": self.param_count,
                "clip_nonnegative": clip_nonnegative,
            },
        }

    def predict_persistence(
        self,
        observations: dict[str, Any],
        variable: str = "temperature_2m",
        horizon: int = FORECAST_HORIZON,
        mode: str = "diurnal",
    ) -> dict[str, Any]:
        """Generate a baseline persistence forecast.

        mode='last_value': Repeats the last observed value across the horizon.
        mode='diurnal': Repeats the last 24-hour cycle across the horizon.
        """
        var_entry = observations.get("variables", {}).get(variable)
        if not var_entry:
            raise KeyError(f"Variable '{variable}' not found in observations dictionary.")

        raw_values = var_entry.get("values", [])
        timestamps = observations.get("timestamps", [])
        if not raw_values:
            raise ValueError(f"No values for variable '{variable}'.")

        # Find last valid value
        valid_vals = [v for v in raw_values if v is not None and not (isinstance(v, float) and math.isnan(v))]
        if not valid_vals:
            raise ValueError(f"No valid numeric observations for '{variable}'.")

        last_valid = valid_vals[-1]
        last_time = timestamps[-1]

        if mode == "diurnal" and len(valid_vals) >= 24:
            cycle = valid_vals[-24:]
            preds = [cycle[i % 24] for i in range(horizon)]
        else:
            preds = [last_valid] * horizon

        future_times = self.generate_future_timestamps(last_time, horizon)

        return {
            "model_id": f"baseline_persistence_{mode}",
            "method": f"persistence_{mode}",
            "variable": variable,
            "unit": VARIABLE_UNITS.get(variable, var_entry.get("unit", "")),
            "context_length_hours": 24 if mode == "diurnal" else 1,
            "forecast_horizon_hours": horizon,
            "forecast_timestamps": future_times,
            "forecast_values": [float(p) for p in preds],
            "metadata": {
                "persistence_mode": mode,
                "last_observed_value": float(last_valid),
                "last_observed_timestamp": last_time,
            },
        }
