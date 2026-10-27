"""CLI interface for LifelineTwin Phase 3: Environmental Intelligence & Forecasting."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .assessment import generate_environmental_assessment
from .evaluation import evaluate_forecast
from .forecasting import TTMForecaster
from .weather import get_observations, STUDY_AREA


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="LifelineTwin Phase 3: Environmental Intelligence & Pretrained Forecasting"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command: fetch
    p_fetch = subparsers.add_parser("fetch", help="Fetch and cache environmental observations")
    p_fetch.add_argument("--cache-dir", default="data/heidelberg/weather", help="Cache directory")
    p_fetch.add_argument("--past-days", type=int, default=30, help="Days of past observations")
    p_fetch.add_argument("--forecast-days", type=int, default=7, help="Days of forecast window")
    p_fetch.add_argument("--force-fresh", action="store_true", help="Bypass local cache")

    # Command: forecast
    p_fc = subparsers.add_parser("forecast", help="Generate pretrained AI forecast")
    p_fc.add_argument("--cache-dir", default="data/heidelberg/weather", help="Cache directory")
    p_fc.add_argument("--variable", default="temperature_2m", help="Weather variable to forecast")
    p_fc.add_argument("--baseline", action="store_true", help="Run persistence baseline instead of TTM")

    # Command: evaluate
    p_ev = subparsers.add_parser("evaluate", help="Evaluate model predictions against historical ground truth")
    p_ev.add_argument("--cache-dir", default="data/heidelberg/weather", help="Cache directory")
    p_ev.add_argument("--variable", default="temperature_2m", help="Variable to evaluate")
    p_ev.add_argument("--horizon", type=int, default=96, help="Evaluation horizon in hours")

    # Command: assess
    p_as = subparsers.add_parser("assess", help="Produce location-specific geographic environmental assessment")
    p_as.add_argument("--cache-dir", default="data/heidelberg/weather", help="Cache directory")
    p_as.add_argument("--variable", default="temperature_2m", help="Weather variable to forecast")

    # Command: all
    p_all = subparsers.add_parser("all", help="Run full Phase 3 pipeline end-to-end")
    p_all.add_argument("--cache-dir", default="data/heidelberg/weather", help="Cache directory")
    p_all.add_argument("--variable", default="temperature_2m", help="Target variable")

    args = parser.parse_args()

    if args.command == "fetch":
        obs = get_observations(
            cache_dir=args.cache_dir,
            past_days=args.past_days,
            forecast_days=args.forecast_days,
            force_fresh=args.force_fresh,
        )
        print(json.dumps({
            "status": "ok",
            "source": obs.get("source"),
            "n_hours": obs.get("n_hours"),
            "cache_hit": obs.get("cache_hit"),
            "variables": list(obs.get("variables", {}).keys()),
        }, indent=2))

    elif args.command == "forecast":
        obs = get_observations(cache_dir=args.cache_dir)
        forecaster = TTMForecaster()
        if args.baseline:
            res = forecaster.predict_persistence(obs, variable=args.variable)
        else:
            res = forecaster.predict(obs, variable=args.variable)
        print(json.dumps(res, indent=2))

    elif args.command == "evaluate":
        obs = get_observations(cache_dir=args.cache_dir)
        ev = evaluate_forecast(obs, variable=args.variable, horizon=args.horizon)
        print(json.dumps(ev, indent=2))

    elif args.command == "assess":
        obs = get_observations(cache_dir=args.cache_dir)
        forecaster = TTMForecaster()
        fc = forecaster.predict(obs, variable=args.variable)
        assessment = generate_environmental_assessment(obs, forecast=fc, study_area=STUDY_AREA)
        print(json.dumps(assessment, indent=2))

    elif args.command == "all":
        obs = get_observations(cache_dir=args.cache_dir)
        forecaster = TTMForecaster()
        fc = forecaster.predict(obs, variable=args.variable)
        ev = evaluate_forecast(obs, variable=args.variable, forecaster=forecaster)
        assessment = generate_environmental_assessment(obs, forecast=fc, study_area=STUDY_AREA)

        output = {
            "pipeline": "Phase 3 Environmental Intelligence & Pretrained Forecasting",
            "study_area": STUDY_AREA["name"],
            "observation_hours": obs["n_hours"],
            "cache_hit": obs.get("cache_hit", False),
            "forecast_sample": {
                "model": fc["model_id"],
                "horizon": fc["forecast_horizon_hours"],
                "variable": fc["variable"],
                "unit": fc["unit"],
                "values_first_5": fc["forecast_values"][:5],
            },
            "evaluation_metrics": ev["models"],
            "best_model_by_mae": ev["comparison"]["best_by_mae"],
            "environmental_assessment": assessment,
        }
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
