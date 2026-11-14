"""LifelineTwin Geospatial & Environmental Resilience Intelligence Package."""

from importlib import import_module

from .weather import (
    STUDY_AREA,
    HOURLY_VARIABLES,
    VARIABLE_UNITS,
    fetch_forecast,
    fetch_historical,
    get_observations,
    load_observations,
    save_observations,
)
from .assessment import (
    generate_environmental_assessment,
    assess_environmental_risks,
)

# Geographic imports must also work in deployments without PyTorch.
_OPTIONAL_EXPORTS = {
    "TTMForecaster": ".forecasting",
    "CONTEXT_LENGTH": ".forecasting",
    "FORECAST_HORIZON": ".forecasting",
    "calculate_metrics": ".evaluation",
    "evaluate_forecast": ".evaluation",
}


def __getattr__(name):
    module = _OPTIONAL_EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module, __name__), name)

__all__ = [
    "STUDY_AREA",
    "HOURLY_VARIABLES",
    "VARIABLE_UNITS",
    "fetch_forecast",
    "fetch_historical",
    "get_observations",
    "load_observations",
    "save_observations",
    "TTMForecaster",
    "CONTEXT_LENGTH",
    "FORECAST_HORIZON",
    "calculate_metrics",
    "evaluate_forecast",
    "generate_environmental_assessment",
    "assess_environmental_risks",
]
